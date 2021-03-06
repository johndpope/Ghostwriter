"""This class executes the lyric generation program."""
#!/usr/bin/python
import re
import sys
import string
from nltk import pos_tag, word_tokenize
from nltk.corpus import cmudict
from pos import Pos
from contractions import contractions

SONG_TITLES = []
PARTS_OF_SPEECH = {}
PUNC = set(string.punctuation)
CMU = cmudict.dict()
FIRST_COMBO = ""
LINES = 0
AVG_SYL = 0

def get_lyrics_from_in_file(lyric_corpus):
    """Reads lyrics from an input and returns a dictionary of song titles containing lyrics."""
    with open(lyric_corpus, "r") as open_corpus:
        print "Obtaining lyrics..."
        raw_text = open_corpus.readlines()
        lyrics = ""

        for line in raw_text:
            # Ensure that line is not whitespace
            if line.strip():
                if line[0] == "(":
                    continue
                elif line[0] == "[":
                    title = re.sub(r"\[", "", line)
                    title = re.sub(r"\]", "", title)
                    stripped = title.strip()
                    current_title = stripped
                    SONG_TITLES.append(current_title)
                else:
                    global LINES
                    LINES += 1
                    this_line = re.sub(r"\)", "", line)
                    this_line = re.sub(r"\(", "", line)
                    lyrics += this_line.strip() + " "
            elif len(lyrics) > 0 and lyrics[len(lyrics)-1] != "\n":
                lyrics += ".\n"   # Cheating to get the songs to recognize ends of lines.
        # Add the last song and return
        return lyrics

def add_tag_combo(two_tags_ago, last_tag, pos_string):
    """Builds a new tag combo and adds it to the POS dict."""
    tag_combo = two_tags_ago + ":" + last_tag
    if len(FIRST_COMBO) == 0:
        global FIRST_COMBO
        FIRST_COMBO = tag_combo
    if tag_combo not in PARTS_OF_SPEECH:
        PARTS_OF_SPEECH[tag_combo] = Pos(tag_combo)
    PARTS_OF_SPEECH[tag_combo].add_next_pos(pos_string)
    return tag_combo


def determine_tags(lyrics):
    """This function reads in a dictionary of songs, then breaks down their tags."""
    print "Determining tags..."
    tagged = pos_tag(word_tokenize(lyrics))
    last_tag = ""
    two_tags_ago = ""
    last_word = ""
    two_words_ago = ""
    syl_count = 0
    for index, word_with_token in enumerate(tagged):
        this_word = word_with_token[0]
        pos_string = word_with_token[1]
        if pos_string in PUNC or this_word[0] == "`" or pos_string == '\'\'':
            last_tag = ""
            last_word = ""
            continue

        try:
            syl_count += nsyl(this_word)[0]
        except KeyError:
            syl_count += 0

        if len(last_tag) == 0 or len(two_tags_ago) == 0:
            two_tags_ago = last_tag
            last_tag = pos_string
            two_words_ago = last_word
            last_word = this_word
        else:
            if last_word[0] == '\'' or two_words_ago[len(two_words_ago)-1] == '\'':
                tag_combo = add_tag_combo(two_tags_ago, last_tag, pos_string)
                PARTS_OF_SPEECH[tag_combo].add_phrase(two_words_ago.rstrip() + last_word)
            elif last_word[0] not in PUNC and two_words_ago[len(two_words_ago)-1] not in PUNC:
                tag_combo = add_tag_combo(two_tags_ago, last_tag, pos_string)
                PARTS_OF_SPEECH[tag_combo].add_phrase(two_words_ago + " " + last_word)

            two_tags_ago = last_tag
            last_tag = pos_string
            two_words_ago = last_word
            last_word = this_word

        if pos_string not in PARTS_OF_SPEECH:
            PARTS_OF_SPEECH[pos_string] = Pos(pos_string)

        if this_word[0] == "\'":
            if tagged[index-1][0].rstrip()+this_word in contractions:
                this_word = tagged[index-1][0].rstrip()+this_word
                PARTS_OF_SPEECH[pos_string].add_phrase(this_word)
        else:
            PARTS_OF_SPEECH[pos_string].add_phrase(this_word)

        if index < len(tagged) - 1:
            if tagged[index+1][1] not in PUNC and tagged[index+1][0] != '\'\'' and tagged[index+1][0] != '``':
                PARTS_OF_SPEECH[pos_string].add_next_pos(tagged[index+1][1])

    global AVG_SYL
    AVG_SYL = syl_count / LINES
    # Set the markov values for each new POS in our existing POS objects.
    for tags in PARTS_OF_SPEECH.keys():
        this_pos = PARTS_OF_SPEECH[tags]
        this_pos.set_markov()

def generate():
    """Generates random lyrics using Markov Chaining."""
    print "Generating song..."
    line_count = 1
    delimiter = ':'
    parsed = FIRST_COMBO.split(delimiter)
    pos_1 = parsed[0]
    pos_2 = parsed[1]
    cmu_entries = cmudict.entries()
    to_rhyme = "boat"
    output = ""
    while line_count < 41:
        syllable_count = 0
        while syllable_count < AVG_SYL:

            addendum = " "
            current_combo = pos_1 + delimiter + pos_2

            if current_combo in PARTS_OF_SPEECH:
                this_pos = PARTS_OF_SPEECH[current_combo]
            else:
                this_pos = PARTS_OF_SPEECH[pos_1]

            random_word = this_pos.get_random_word()

            try:
                syllable_count += nsyl(random_word)[0]
            except KeyError:
                syllable_count += 1

            pos_1 = this_pos.get_random_pos()
            current_combo = pos_2 + pos_1

            if current_combo in PARTS_OF_SPEECH:
                pos_2 = PARTS_OF_SPEECH[current_combo].get_random_pos()
            else:
                pos_2 = PARTS_OF_SPEECH[pos_1].get_random_pos()

            if syllable_count >= AVG_SYL:
                addendum = "\n"
                # Try to find a rhyme if possible.
                if len(to_rhyme) > 0:
                    random_word = this_pos.find_rhyme(to_rhyme, cmu_entries)
                    to_rhyme = ""
                else:
                    if random_word.find(' ') > -1:
                        to_rhyme = random_word.split(' ')[1]
                    else:
                        to_rhyme = random_word
                if line_count % 8 == 0:
                    parsed = FIRST_COMBO.split(delimiter)
                    pos_1 = parsed[0]
                    pos_2 = parsed[1]
                    addendum = "\n\n"
            output += random_word + addendum

        buffer_val = float(100) / 41
        percentage = "{0:.0f}%".format(buffer_val * line_count)
        print percentage + " complete"
        line_count += 1

    print "\n\nCOMPLETE!! Here is your new Smash Hit:\n"
    print output

def nsyl(word):
    """Gets the number of syllables for a given word."""
    return [len(list(y for y in x if y[-1].isdigit())) for x in CMU[word.lower()]]

def print_footnote():
    """Prints the footnote message"""
    footnote = "Data gathered from "
    for index, title in enumerate(SONG_TITLES):
        if index < len(SONG_TITLES) - 1:
            footnote += title + ", "
        else:
            footnote += "and " + title

    artist = sys.argv[1].split(".")
    footnote += " by " + artist[0].title() + "\n"
    print footnote

def main():
    """Launches the program."""
    reload(sys)
    sys.setdefaultencoding("utf-8")
    lyrics = get_lyrics_from_in_file(sys.argv[1])
    determine_tags(lyrics)
    generate()
    print_footnote()

if __name__ == '__main__':
    main()
