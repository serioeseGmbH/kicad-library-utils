#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from json import load
from errno import ENOENT, EINVAL
from re import compile as regex
from sch import *

def parse_arguments():
    parser = ArgumentParser(description='Tool to assign MPNs to symbols in a KiCAD schematic')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v",  "--verbose",     action = "store_true",        help = 'doesn\'t do anything ATM')
    parser.add_argument('-s', "--schematic",   type = str, required=True,    help='path to .sch file')
    parser.add_argument('-l', "--lookuptable", type = str, required=True,    help='path to mpn lookup table')
    args = parser.parse_args()
    return args

def read_schematic(path):
    try:
        return Schematic(path)
    except FileNotFoundError as fnfe:
        print(fnfe)
        print("Could not find schematic file")
        exit(ENOENT)

def read_lut(path):
    try:
        return load(open(path, 'r'))
    except FileNotFoundError as fnfe:
        print(fnfe)
        print("Could not find lookup table file")
        exit(ENOENT)
    except json.decoder.JSONDecodeError as jsone:
        print(jsone)
        print("Could not read lookup table file")
        exit(EINVAL)

def main():
    args     = parse_arguments()
    sch      = read_schematic(args.schematic)
    part_lut = read_lut(args.lookuptable)
    cat_expr = regex('[a-zA-Z]+')

    for component in sch.components:
        if '#PWR' in component.fields[0]['ref'] or\
           'PWR_FLAG' in component.fields[1]['ref']:
            continue

        Reference = component.fields[0]["ref"].replace('"', '')
        category  = cat_expr.match(Reference).group()
        datasheet_field = component.fields[3]
        mpn_field = None

        # Buildtuple of identifying properties
        sch_tuple = {
            "Value"     : component.fields[1]["ref"].replace('"', ''),
            "Footprint" : component.fields[2]["ref"].replace('"', ''),
        }
        for field in component.fields[4:]:
            key   = field["name"].replace('"', '')
            value = field["ref"].replace('"', '')
            if key != "MPN":
                sch_tuple.update({key : value})
            else:
                mpn_field = field

        if not mpn_field:
            mpn_field = component.addField({'name': '"MPN"', 'ref': '""'})

        # Try to match tuple
        if category in part_lut:
            found = False
            for part in part_lut[category]:
                part_tuple = part.copy()
                try:
                    part_tuple.pop("MPN") 
                    part_tuple.pop("Datasheet")
                except KeyError as ke:
                    print("{} missing for {}: {}".format(ke, category, part))
                    pass
                # In case of match, assign MPN and Datasheet
                if(part_tuple == sch_tuple):
                    found = True
                    mpn_field["ref"] = "\"{}\"".format(part["MPN"])
                    datasheet_field["ref"] = "\"{}\"".format(part["Datasheet"])
                    break
            if not found:
                print("No part found for {}: {}".format(Reference, sch_tuple))
        else:
            print("Category {} not found".format(category))
    sch.save()

if __name__ == "__main__":
    main()
