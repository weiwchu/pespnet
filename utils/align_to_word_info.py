#!/usr/bin/env python3
import argparse
import logging
import sys

from espnet.transform.transformation import Transformation
from espnet.utils.cli_readers import file_reader_helper
from espnet.utils.cli_utils import get_commandline_args
from espnet.utils.cli_utils import is_scipy_wav_style


def get_parser():
    parser = argparse.ArgumentParser(
        description="convert alignment info to word info",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--verbose", "-V", default=0, type=int, help="Verbose option")
    parser.add_argument(
        "--align-info-list",
        type=str,
        default=None,
        help="The alignment infomation list",
    )
    parser.add_argument(
        "--utt-list-file",
        type=str,
        default=None,
        help="The utterence list file",
    )
    parser.add_argument(
        "out",
        nargs="?",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="The output filename. " "If omitted, then output to sys.stdout",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    # logging info
    logfmt = "%(asctime)s (%(module)s:%(lineno)d) %(levelname)s: %(message)s"
    if args.verbose > 0:
        logging.basicConfig(level=logging.INFO, format=logfmt)
    else:
        logging.basicConfig(level=logging.WARN, format=logfmt)
    logging.info(get_commandline_args())

    if args.align_info_list is None:
        logging.error("No --align-info-list input")
    hwords = {}
    with open(args.align_info_list) as f:
        for align_info_file in f.readlines():
            with open(align_info_file.strip()) as g:
                for line in g.readlines():
                    # 8842-302201-0002 ",BUT,WHEN,I,STIL.. ," "0.290,0.430,0.560, ..." # ending_times
                    word_info = []
                    args.out.write(line + "\n")
                    args.out.write(args.align_info_list + "\n")
                    uttid, text_str, time_str = line.split()
                    words = text_str.replace('"','').split(',')
                    end_times = time_str.replace('"','').split(',')
                    start_time = 0
                    for word, end_time in zip(words, end_times):
                        end_time = float(end_time)
                        word_info.append((word, start_time, end_time))
                        start_time = end_time
                    hwords[uttid] = word_info
    
    if args.utt_list_file is None:
        logging.error("No --utt-list-file input")

    # currently use uniform probabilites for words
    prob = 1.0
    with open(args.utt_list_file) as f:
        for line in f.readlines():
            uttid = line.strip()
            args.out.write("({} )".format(uttid))
            if uttid in hwords:
                # uttid (0.0 0.20 1.0 '') (0.20 0.78 1.0 'WE')
                for word, start_time, end_time in hwords[uttid]:
                    args.out.write("({:d} {:d} {:.4f} '{}')".format(int(start_time*100), int(end_time*100), prob, word))
            else:
                # no valid alignment
                args.out.write("(0 0 1.000 '')")
            args.out.write("\n")

if __name__ == "__main__":
    main()
