import regex as re
from nltk.tokenize import sent_tokenize
from datetime import datetime
import os
from zipfile import ZipFile
import sys
import getopt

SUPERSCRIPT_LEGEND = {
    "1":"\u00B9",
    "2":"\u00B2",
    "3":"\u00B3",
    "4":"\u2074",
    "5":"\u2075",
    "6":"\u2076",
    "7":"\u2077",
    "8":"\u2078",
    "9":"\u2079",
    "0":"\u2070",
    "x":"\u02E3"
    }

CAPITALIZED_WORDS = {
    "(?<=^|[\n\W])[Hh][Qq](?=$|[\n\W])":"HQ",
    "(?<=^|[\n\W])[Rr]&[Dd](?=$|[\n\W])":"R&D",
    "(?<=^|[\n\W])[Aa][Rr][Cc][Hh][Ii][Vv][Ee][Ss](?=$|[\n\W])":"Archives",
    "(?<=^|[\n\W])[Rr][Uu][Nn][Nn][Ee][Rr](?=$|[\n\W])":"Runner",
    "(?<=^|[\n\W])[Cc][Oo][Rr][Pp](?=$|[\n\W])":"Corp",
    "(?<=^|[\n\W])[Aa][Pp](?=$|[\n\W])":"AP",
    "(?<=^|[\n\W])[Aa][Ii](?=$|[\n\W])":"AI",
    "(?<=^|[\n\W])x(?=$|[\n\W])":"X",
    "<sym>[Ss][Ss][Ss][Uu][Bb]<\/sym>":"<sym>ssSub</sym>",
    "<sym>[Ss][Ss][Cc][Ll][Ii][Cc][Kk]<\/sym>":"<sym>ssClick</sym>",
    "<sym>[Ss][Ss][Cc][Rr][Ee][Dd][Ii][Tt]<\/sym>":"<sym>ssCredit</sym>",
    "<sym>[Ss][Ss][Ll][Ii][Nn][Kk]<\/sym>":"<sym>ssLink</sym>",
    "<sym>[Ss][Ss][Mm][Uu]<\/sym>":"<sym>ssMU</sym>",
    "<sym>[Ss][Ss][Rr][Ee][Cc][Uu][Rr][Rr][Ee][Nn][Tt]<\/sym>":"<sym>ssRecurrent</sym>",
    "<sym>[Ss][Ss][Tt][Rr][Aa][Ss][Hh]<\/sym>":"<sym>ssTrash</sym>",
    }
    
RUNNER_FACTIONS = ["shaper", "criminal", "anarch", "sunny", "apex", "adam"]
CORP_FACTIONS = ["weyland", "hb", "nbn", "jinteki"]
NOTES_SUB = [["<sym>ssSub</sym>", ":subroutine:"], ["<sym>ssLink</sym>", ":link~1:"], ["<sym>ssCredit</sym>", ":credit:"], ["<sym>ssClick</sym>", ":click:"], ["<sym>ssTrash</sym>", ":trash:"], ["<sym>ssMU</sym>", ":mu:"], ["<sym>ssRecurrent</sym>", ":recurring-credit:"]]
def text_casing(input_text):
    sentences = sent_tokenize(input_text, language='english')
    sentences_capitalized = [s.capitalize() for s in sentences]
    text_truecase = re.sub(" (?=[\.,'!?:;])", "", ' '.join(sentences_capitalized))
    return text_truecase

def capitalize_titles(field):
    result = field.title()
    for word in CAPITALIZED_WORDS:
        result = re.sub(word, CAPITALIZED_WORDS[word], result)
        return result

def get_num_value(match_obj):
    if match_obj.group(2) == "x" or match_obj.group(2) == "X":
        result = "***"
    else:
        result = str(len(match_obj.group(2)))
    if match_obj.group(1) == "&":
        return result
    elif match_obj.group(1) == "{#}":
        result = ""
        if result == "***":
            result = SUPERSCRIPT_LEGEND["x"]
        else:
            for digit in str(len(match_obj.group(2))):
                result += SUPERSCRIPT_LEGEND[digit]
        return "Trace" + result + " – "
    elif match_obj.group(1) == "{C}":
        return result + "<sym>ssCredit</sym>"
    elif match_obj.group(1) == "{L}":
        return result + "<sym>ssLink</sym>"
    elif match_obj.group(1) == "{M}":
        return result + "<sym>ssMU</sym>"
    elif match_obj.group(1) == "{R}":
        return result + "<sym>ssRecurrent</sym>"
    
def remove_choice_formatting(match_obj):
    result = match_obj.group(1) + match_obj.group(2)
    result = re.sub("=", "\n\t\u2022 ", result)
    return result

def get_cap_letter(match_obj):
    result = match_obj.group(1).upper()
    if result[0] == " ":
        return result
    else:
        return " " + result

def get_superscript_num_value(match_obj):
    result = ""
    for digit in str(len(match_obj.group(2))):
        result += SUPERSCRIPT_LEGEND[digit]
    return result

def pre_process_cards(side, file_name, time, time_edited, output_name):
    raw_cards = []
    try:
        f = open(file_name, "r", encoding = "utf-8", errors = "ignore")
    except OSError:
        print(f'file {file_name} does not exist. Please use --input to specify the file.')
        quit()
    for line in f:
        if line != "\n":
            raw_cards.append(line)
    f.close()
    #Dirty way to estimate if we need to process as runner or corp when --side is not provided
    if side != "corp" and side != "runner":
        print("WARNING: Please use --side to specify runner or corp")
        print("Determining side...")
        runner_count = 0
        corp_count = 0
        for card in raw_cards:
            for faction in RUNNER_FACTIONS:
                if faction in card:
                    runner_count += 1
                    break
            for faction in CORP_FACTIONS:
                if faction in card:
                    corp_count += 1
                    break
        if runner_count >= corp_count:
            side = "runner"
        else:
            side = "corp"
        print(f"Processing cards as {side}.")
    #Convert results to raw strings
    for index, card in enumerate(raw_cards):
        raw_cards[index] = (r'%s' %card)
    #Decode encoded syntax back to human readable form
    for index, card in enumerate(raw_cards):
        raw_cards[index] = raw_cards[index].replace("\\", "\n\n")
        raw_cards[index] = re.sub(">", "<sym>ssSub</sym>", raw_cards[index])
        raw_cards[index] = re.sub("\[\((.+?)\)(.+?)\]", remove_choice_formatting, raw_cards[index])
        raw_cards[index] = re.sub("=", "\n\t\u2022", raw_cards[index])
        raw_cards[index] = re.sub("((?<![rR])&(?![dD])|{#}|{C}|{L}|{M}|{R})([Xx]|\^*)", get_num_value, raw_cards[index])
        raw_cards[index] = re.sub("{O}", "<sym>ssClick</sym>", raw_cards[index])
        raw_cards[index] = re.sub("{T}", "<sym>ssTrash</sym>", raw_cards[index])
    #Process cards depending on --side
    print("Creating MSE file...")
    file_info = process_cards(raw_cards, time, time_edited, side)
    #Create MSE file
    if os.path.exists("set"):
        os.remove("set")
    os.rename("output.txt","set")
    zip_set = ZipFile(f"{output_name}.zip", 'w')
    zip_set.write('set')
    zip_set.close()
    os.rename(f"{output_name}.zip", f"{output_name}.mse-set")
    os.remove("set")
    if file_info[2] == 1:
    	print ("1 card was unable to be parsed.")
    elif file_info[2] == 0:
        pass
    else:
        print (f"{file_info[2]} cards were unable to be parsed.")
    print (f"{file_info[1]} {file_info[0]} cards generated as {output_name}.mse-set!")

#These functions could be compressed a lot if I wanted to put the effort into it. But hey, it works just fine.
def process_cards(raw_cards, time, time_edited, side):
    cards_parsed = 0
    not_parsed = 0
    with open("output.txt", "w") as f:
        f.write("mse version: 0.3.8\n"
                "game: androidnetrunner\n"
                "stylesheet: corpice\n")
        for index, card in enumerate(raw_cards):
            we_good = True
            has_trash_cost = 0
            fields = {}
            fields["card_type"] = re.findall("\|1([^0-4][^\|]*)\|", card)
            fields["keywords"] = re.findall("\|2([^\|]*)\|", card)
            fields["faction"] = re.findall("\|3([^\|]*)\|", card)
            fields["influence"] = re.findall("\|4([^\|]*)\|", card)
            fields["strength"] = re.findall("\|5([^\|]*)\|", card)
            fields["unique"] = re.findall("\|6([^\|]*)\|", card)
            # Field 7 refers to either starting link or advancement cost
            fields["field_7"] = re.findall("\|7([^\|]*)\|", card)
            # Field 8 refers to either memory cost or agenda points
            fields["field_8"] = re.findall("\|8([^\|]*)\|", card)
            fields["influence_limit"] = re.findall("\|9([^\|]*)\|", card)
            fields["deck_size"] = re.findall("\|10([^\|]*)\|", card)
            fields["text"] = re.findall("\|11([^\|]*)\|", card)
            fields["cost"] = re.findall("\|12([^\|]*)\|", card)
            fields["title"] = re.findall("\|13([^\|]*)\|", card)
            if "corp" in side:
                fields["trash_cost"] = re.findall("\|14([^\|]*)\|", card)
            else:
                fields["trash_cost"] = "NA"
            for field in fields:
                if not fields[field]:
                    not_parsed += 1
                    we_good = False
                    break
            if not we_good:
                continue
            for field in fields:
                fields[field] = fields[field][0]
            fields["keywords"] = capitalize_titles(fields["keywords"])
            fields["keywords"] = fields["keywords"].split(", ")
            keywords_string = ""
            for keyword in fields["keywords"]:
                keywords_string += keyword
                keywords_string += " - "
            fields["keywords"] = keywords_string[:-3]
            for word in CAPITALIZED_WORDS:
                fields["keywords"] = re.sub(word, CAPITALIZED_WORDS[word], fields["keywords"])
            if fields["faction"] == "hb":
                fields["faction"] = "haas-bioroid"
            fields["title"] = fields["title"].title()
            fields["text"] = fields["text"].split("\n")
            fields["text"] = [value for value in fields["text"] if value != ""]
            for index, line in enumerate(fields["text"]):
                fields["text"][index] = text_casing(line)
            fields["text"] = "\n\t\t".join(fields["text"])
            fields["text"] = re.sub("@", fields["title"], fields["text"])
            for word in CAPITALIZED_WORDS:
                fields["text"] = re.sub(word, CAPITALIZED_WORDS[word], fields["text"])
            fields["text"] = re.sub("(?<=<sym>ssSub<\/sym>|\u2022)( *.)", get_cap_letter, fields["text"])
            fields["text"] = re.sub("\*\*\*", "X", fields["text"])
            if fields["unique"] == "true":
                fields["title"] = "<sym>ssDiamond</sym> " + fields["title"]
            if fields["trash_cost"] != "":
                has_trash_cost = 1
            fields["notes_title"] = fields["title"].replace("<sym>ssDiamond</sym>", "\u2b25")
            fields["notes_text"] = fields["text"].replace("<sym>ssSub</sym>", ":subroutine:")
            for sub in NOTES_SUB:
                fields["notes_text"] = fields["notes_text"].replace(sub[0], sub[1])
            notes = f"\tnotes:\n\t\t{fields['notes_title']}\n\t\t{fields['card_type'].capitalize()}"
            if fields['keywords'] != "":
                notes += f": {fields['keywords']}"
            notes += "\n\t\t"
            if "identity" in fields['card_type']:
                if "runner" in side:
                    notes+= f"Link: {fields['field_7']} | "
                notes += f"Deck: {fields['deck_size']} | Influence: {fields['influence_limit']}\n\t\t"
            else:
                if "agenda" in fields['card_type']:
                    notes += f"Adv: {fields['field_7']} | Score: {fields['field_8']}"
                elif "operation" in fields['card_type'] or "event" in fields['card_type']:
                    notes += f"Cost: {fields['cost']}"
                elif "corp" in side:
                    notes += f"Rez: {fields['cost']}"
                else:
                    notes += f"Install: {fields['cost']}"
                if "ice" in fields['card_type'] or "program" in fields['card_type']:
                    if "program" in fields['card_type']:
                        notes += f" | Memory: {fields['field_8']}"
                    notes += f" | Strength: {fields['strength']}"
                if has_trash_cost and "corp" in side:
                    notes += f" | Trash: {fields['trash_cost']}"
                if ("agenda" in fields['card_type'] and "neutral" in fields['faction']) or not "agenda" in fields['card_type']:
                    notes+= f" | Influence: {fields['influence']}"
                notes += "\n\t\t"
            notes += f"{fields['notes_text']}\n\t\t"
            if fields['faction'] == "nbn":
                fields['notes_faction'] = "NBN"
            elif fields['faction'] == "haas-bioroid":
                fields['notes_faction'] = "Haas-Bioroid"
            else:
                fields['notes_faction'] = text_casing(fields['faction'])
            notes += f"RRC | {fields['notes_faction']}\n"
            if re.search("identity|asset|operation|upgrade|agenda|ice|resource|program|hardware|event", fields["card_type"]) \
            and re.search("neutral|jinteki|haas-bioroid|nbn|weyland|shaper|criminal|anarch|sunny|adam|apex", fields["faction"]) \
            and fields["influence"].isdigit():
                f.write("card:\n")
                f.write("\thas styling: false\n")
                f.write("\tartwork: \n")
                f.write(f"\ttime created: {time[:-7]}\n")
                f.write(f"\ttime modified: {time[:-7]}\n")
                f.write(f"\t{side}faction: {fields['faction']}\n")
                f.write(f"\tstylesheet: {side}{fields['card_type']}\n")
                f.write("\ttext:\n")
                f.write(f"\t\t{fields['text']}\n")
                f.write(f"\tkeywords: <i>{fields['card_type'].upper()}")
                if fields['keywords']:
                    f.write(f":</i> {fields['keywords']}\n")
                else:
                    f.write("</i>\n")
                f.write(notes)
                if "identity" in fields["card_type"]:
                    split_title = re.search("(.*):(.*)", fields["title"])
                    if split_title:
                        f.write(f"\ttitle: {split_title.group(1)}\n")
                        f.write(f"\tsubtitle: {split_title.group(2)}\n")
                    else:
                        f.write(f"\ttitle: {fields['title']}\n")
                        f.write("\tsubtitle: \n")
                    f.write(f"\tdecksize: {fields['deck_size']}\n")
                    f.write(f"\tinfluencelimit: {fields['influence_limit']}\n")
                    if "runner" in side:
                        f.write(f"\tstartinglink: {fields['field_7']}\n")
                else:
                    f.write(f"\ttitle: <b>{fields['title']}</b>\n")
                    if "corp" in side:
                        if has_trash_cost:
                            f.write("\ttrashicon: 1\n")
                        else:
                            f.write("\ttrashicon: 0\n")
                        f.write(f"\ttrashcost: {fields['trash_cost']}\n")
                    if "agenda" in fields["card_type"]:
                        try:
                            if int(fields['field_7']) <= 9:
                                f.write(f"\tadvancementrequirement: <sym>ssad{fields['field_7']}</sym>\n")
                            else: 
                                f.write(f"\tadvancementrequirement: {fields['field_7']}\n")
                        except ValueError:
                            f.write(f"\tadvancementrequirement: {fields['field_7']}\n")
                        try:
                            if int(fields['field_8']) <= 9:
                                f.write(f"\tagendapoints: <sym>ssag{fields['field_8']}</sym>\n")
                            else: 
                                f.write(f"\tagendapoints: {fields['field_8']}\n")
                        except ValueError:
                    	    f.write(f"\tagendapoints: {fields['field_8']}\n")
                        if fields['faction'] == "neutral":
                            f.write(f"\tinfluence: {fields['influence']}\n")
                        else:
                            f.write(f"\tinfluence: 0\n")
                    else:
                        if "ice" in fields["card_type"]:
                            if fields['strength'] == "":
                                fields['strength'] = "0"
                            f.write(f"\tstrength: {fields['strength']}\n")
                        if "program" in fields['card_type']:
                            if fields['strength'] == "":
                                fields['strength'] = "\u2013"
                            f.write(f"\tstrength: {fields['strength']}\n")
                            try:
                    	         if int(fields['field_8']) < 10:
                                    f.write(f"\tmu: <sym>ss{fields['field_8']}</sym>\n")
                    	         else:
                    	             f.write(f"\tmu: {fields['field_8']}\n")
                            except ValueError:
                    	         f.write(f"\tmu: {fields['field_8']}\n")
                        f.write(f"\tcost: {fields['cost']}\n")
                        f.write(f"\tinfluence: {fields['influence']}\n")
            else:
                not_parsed += 1
                we_good = False
                continue
            cards_parsed += 1
        f.write("version control: \n"
                "	type: none\n"
                "apprentice code: ")
    f.close()
    return side, cards_parsed, not_parsed
    
#Get arguments
argv = sys.argv[1:]
opts, args = getopt.getopt(argv, "", ["side=", "input=", "output="])
side = None
input_file = None
output_name = None
for opt, arg in opts:
    if opt in ['--side']:
        opt_lower = arg.lower()
        side = opt_lower
    elif opt in ['--input']:
        input_file = arg
    elif opt in ['--output']:
        output_name = arg
#We use the current date time for the output file name and it's useful for creating the MSE file as well.
time = datetime.now()
time = str(time)
time_edited = re.sub("-|:|\.", "_", time)  
if side == None:
    side = "undefined"
if input_file == None:
    input_file = "input.txt"
if output_name == None:
    output_name = f"output_{time_edited}"  
pre_process_cards(side, input_file, time, time_edited, output_name)
