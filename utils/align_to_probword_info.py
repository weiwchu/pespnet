#!/usr/bin/env python3
import argparse
import logging
import sys

from espnet.transform.transformation import Transformation
from espnet.utils.cli_readers import file_reader_helper
from espnet.utils.cli_utils import get_commandline_args
from espnet.utils.cli_utils import is_scipy_wav_style

# pip install --user -U arpa
import numpy as np
import arpa

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
        "--arpa-lm-file",
        type=str,
        default=None,
        help="The utterence list file",
    )
    parser.add_argument(
        "--ngram-count",
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
    
    models = arpa.loadf(args.arpa_lm_file)
    lm = models[0]
    ngram_count = int(args.ngram_count)

    hwords = {}
    with open(args.align_info_list) as f:
        for align_info_file in f.readlines():
            with open(align_info_file.strip()) as g:
                for line in g.readlines():
                    # 8842-302201-0002 ",BUT,WHEN,I,STIL.. ," "0.290,0.430,0.560, ..." # ending_times
                    word_info = []
                    uttid, text_str, time_str = line.split()
                    words = text_str.replace('"','').split(',')
                    end_times = time_str.replace('"','').split(',')
                    start_time = 0
                    word_history = []
                    is_in_sentence = False
                    for word, end_time in zip(words, end_times):
                        if word == '':
                            if is_in_sentence is True:
                                word = '</S>'
                            else:
                                word = '<S>'
                                is_in_sentence = True
                        word_history.append(word)
                        if len(word_history) > ngram_count:
                            word_history.pop()
                        word_history_str = " ".join(word_history)
                        logp = lm.log_p(word_history_str)
                        if word == '</S>':
                            word_history = ['<S>']
                            is_in_sentence = True
                        end_time = float(end_time)
                        word_info.append((word, start_time, end_time, logp))
                        start_time = end_time
                    hwords[uttid] = word_info
    
    if args.utt_list_file is None:
        logging.error("No --utt-list-file input")

    # currently use uniform probabilites for words
    with open(args.utt_list_file) as f:
        for line in f.readlines():
            uttid = line.strip()
            args.out.write("{}".format(uttid))
            if uttid in hwords:
                # uttid (0.0 0.20 1.0 '') (0.20 0.78 1.0 'WE')
                sum_logp = -100.0
                for word, start_time, end_time, logp in hwords[uttid]:
                    if word != '<S>' and word != '</S>':
                        sum_logp = np.logaddexp(sum_logp, logp)
                for word, start_time, end_time, logp in hwords[uttid]:
                    if word != '<S>' and word != '</S>':
                        prob = np.exp(logp - sum_logp)
                    else:
                        prob = 0.0
                    args.out.write(" {:d},{:d},{:.4f},{}".format(int(start_time*100), int(end_time*100), prob, word))
            else:
                # no valid alignment
                args.out.write(" 0,0,1.000,''")
            args.out.write("\n")

if __name__ == "__main__":
    main()
