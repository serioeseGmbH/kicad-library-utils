#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from json     import load
from errno    import ENOENT, EINVAL
from re       import compile as regex
from sch      import Schematic
from logging  import getLogger, StreamHandler
from logging  import ERROR, WARNING, INFO, DEBUG, NOTSET

cat_expr = regex('[a-zA-Z]+')

def parse_arguments():
    parser = ArgumentParser(description='Tool to assign MPNs to symbols in a KiCAD schematic')
    mutexg = parser.add_mutually_exclusive_group()
    mutexg.add_argument("-q", "--quiet",       action = "store_true",     help = 'Turn off warnings')
    mutexg.add_argument("-v",                  action = "count",          help = 'Set loglevel')
    parser.add_argument('-s', "--schematic",   type = str, required=True, help = 'path to .sch file')
    parser.add_argument('-l', "--lookuptable", type = str, required=True, help = 'path to mpn lookup table')
    args = parser.parse_args()
    return args

def read_schematic(path):
    try:
        return Schematic(path)
    except FileNotFoundError as fnfe:
        error(fnfe)
        error("Could not find schematic file")
        exit(ENOENT)

def read_lut(path):
    try:
        return load(open(path, 'r'))
    except FileNotFoundError as fnfe:
        log.error(fnfe)
        log.error("Could not find lookup table file")
        exit(ENOENT)
    except json.decoder.JSONDecodeError as jsone:
        log.error(jsone)
        log.error("Could not read lookup table file")
        exit(EINVAL)

def generate_logger(verbose, quiet):
    logger = getLogger()
    logger.addHandler(StreamHandler())
    if verbose:
        if   1 == verbose:
            logger.setLevel(INFO)
            logger.info("Verbose output.")
        elif 2 <= verbose:
            logger.setLevel(DEBUG)
            logger.debug("Debug output.")
    elif quiet:
        logger.setLevel(ERROR)
    return logger

def gen_comp_tuple(component):
    comp_tuple = {
        "Value"     : component.fields[1]["ref"].replace('"', ''),
        "Footprint" : component.fields[2]["ref"].replace('"', ''),
    }
    for field in component.fields[4:]:
        key   = field["name"].replace('"', '')
        value = field["ref"].replace('"', '')
        if key != "MPN":
            comp_tuple.update({key : value})
    return comp_tuple

def gen_part_tuple(part):
    part_tuple = part.copy()
    try:
        part_tuple.pop("MPN") 
        part_tuple.pop("Datasheet")
    except KeyError as ke:
        log.error("{} missing for {}: {}".format(ke, category, part))
    return part_tuple

def component_assert_mpn_field(component):
    mpn_field = None
    for field in component.fields[4:]:
        if "MPN" == field["name"].replace('"', ''):
            mpn_field = field
    if not mpn_field:
        mpn_field = component.addField({'name': '"MPN"', 'ref': '""'})
    return mpn_field

def match_component(component, part_lut):
    # ignore these 
    if '#PWR' in component.fields[0]['ref'] or\
       'PWR_FLAG' in component.fields[1]['ref']:
        return

    Reference  = component.fields[0]["ref"].replace('"', '')
    category   = cat_expr.match(Reference).group()
    datasheet_field = component.fields[3]
    mpn_field  = component_assert_mpn_field(component)
    comp_tuple = gen_comp_tuple(component)

    if category in part_lut:
        found = False
        for part in part_lut[category]:
            # generate reduced dict for matching
            part_tuple = gen_part_tuple(part)
            # in case of match, assign MPN and Datasheet and iterate for next part
            if part_tuple == comp_tuple:
                log.info("Matched {} with {}".format(Reference, part))
                mpn_field["ref"] = "\"{}\"".format(part["MPN"])
                datasheet_field["ref"] = "\"{}\"".format(part["Datasheet"])
                found = True
                break
        if not found:
            log.warning("No part found for {}: {}".format(Reference, comp_tuple))
    else:
        log.warning("Category {} not found".format(category))

def main():
    global log
    args     = parse_arguments()
    log      = generate_logger(args.v, args.quiet)
    sch      = read_schematic(args.schematic)
    part_lut = read_lut(args.lookuptable)

    for component in sch.components:
        match_component(component, part_lut)

    sch.save()

if __name__ == "__main__":
    main()
