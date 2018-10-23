#!/usr/bin/env python2.7

from sch import Schematic
import csv
from argparse import ArgumentParser
from logging  import getLogger, StreamHandler
from logging  import ERROR, WARNING, INFO, DEBUG, NOTSET

REQUIRED_NAMES = ["Reference", "Value", "Footprint", "Datasheet"]
log = None

def parse_arguments():
    parser = ArgumentParser(description='Command line tool to export BOM from KiCAD .sch file as CSV.')
    verbose = parser.add_mutually_exclusive_group()
    verbose.add_argument(  "-q", "--quiet",     action = "store_true",                  help = "turn off warnings")
    verbose.add_argument(  "-v",                action = "count",                       help = "set verbose loglevel")
    parser.add_argument(   "-s", "--schematic", type = str,             required=True,  help = "path to schematic file")
    parser.add_argument(   "-c", "--csv",       type = str,             required=True,  help = "path to CSV file")
    args = parser.parse_args()
    return args

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

def main(path_sch, path_csv):
    # read schematic into Schematic object
    try:
        sch = Schematic(path_sch)
    except IOError:
        print("Could not open schematic file")
        raise

    # generate set of all available names
    names_set = set(REQUIRED_NAMES)
    for comp in sch.components:
        for field in comp.fields[4:]:
            names_set.add(field['name'][1:-1])

    # prepend required names and append rest
    names_list = REQUIRED_NAMES + list(names_set.difference(set(REQUIRED_NAMES)))

    # generate list of dicts of all compoennts in schematic except for power symbols
    comp_dict_list = list()
    for comp in sch.components:
        # skip power symbols
        if comp.fields[0]["ref"][1] is "#":
            continue
        # add mandatory fields to dict
        comp_dict = {
            "Reference" : comp.fields[0]["ref"][1:-1],
            "Value"     : comp.fields[1]["ref"][1:-1],
            "Footprint" : comp.fields[2]["ref"][1:-1],
            "Datasheet" : comp.fields[3]["ref"][1:-1],
        }
        # add optional fields to dict
        for field in comp.fields[4:]:
            comp_dict[field['name'][1:-1]] = field["ref"][1:-1]
        # appent to list
        comp_dict_list.append(comp_dict)

    # sort by component reference designator
    comp_dict_list = sorted(comp_dict_list, key=lambda entry: entry["Reference"])

    # write out to csv
    try:
        with open(path_csv, 'wb') as outcsv:
            writer = csv.writer(outcsv, quoting=csv.QUOTE_ALL)
            writer.writerow(names_list)
            for comp_dict in comp_dict_list:
                writer.writerow([comp_dict[key] if key in comp_dict else '' for key in names_list])
    except IOError:
        print("Could not open csv file")
        raise

if __name__ == "__main__":
    args = parse_arguments()
    log = generate_logger(args.v, args.quiet)
    main(args.schematic, args.csv)
