import json
import re
import io
import copy
import sys
import getopt

#List of all of the fields for each card in the JSON file. Not every card has all of these.
#KEYS = [
#'code',
#'deck_limit',
#'faction_code',
#'faction_cost',
#'flavor',
#'illustrator',
#'influence_limit',
#'keywords',
#'minimum_deck_size',
#'pack_code',
#'position',
#'quantity',
#'side_code',
#'stripped_text',
#'stripped_title',
#'text',
#'title',
#'type_code',
#'uniqueness',
#'base_link',
#'cost',
#'memory_cost',
#'strength',
#'advancement_cost',
#'agenda_points',
#'trash_cost'
#]

#List of the fields we do not need and can discard.
REMOVE = [
'code',
'deck_limit',
'illustrator',
'pack_code',
'position',
'quantity',
'stripped_text',
'stripped_title',
'flavor'
    ]

#List of all the fields after the unneccesary fields have been removed.
#STRIPPED_KEYS = [
#'title',
#'faction_code',
#'faction_cost',
#'influence_limit',
#'keywords',
#'minimum_deck_size',
#'side_code',
#'text',
#'title',
#'type_code',
#'uniqueness',
#'base_link',
#'cost',
#'memory_cost',
#'strength',
#'advancement_cost',
#'agenda_points',
#'trash_cost'
#]

CORP_SIDE = [
["1", 'type_code'],
["2", 'keywords'],
["3", 'faction_code'],
["4", 'faction_cost'],
["5", 'strength'],
["6", 'uniqueness'],
["7", 'advancement_cost'],
["8", 'agenda_points'],
["9", 'influence_limit'],
["10", 'minimum_deck_size'],
["11", 'text'],
["12", 'cost'],
["13", 'title'],
["14", 'trash_cost']
]

RUNNER_SIDE = [
["1", 'type_code'],
["2", 'keywords'],
["3", 'faction_code'],
["4", 'faction_cost'],
["5", 'strength'],
["6", 'uniqueness'],
["7", 'base_link'],
["8", 'memory_cost'],
["9", 'influence_limit'],
["10", 'minimum_deck_size'],
["11", 'text'],
["12", 'cost'],
["13", 'title'],
]

def get_trace_value(match_obj):
    result = "{#}"
    if match_obj.group(1) == "x":
        result += "X"
    else:
        for x in range(0, int(match_obj.group(1))):
            result += "^"
    return result

def get_credit_value(match_obj):
    result = "{C}"
    if match_obj.group(1) == "x":
        result += "X"
    else:
        for x in range(0, int(match_obj.group(1))):
            result += "^"
    return result

def get_link_value(match_obj):
    result = "{L}"
    for x in range(0, int(match_obj.group(1))):
        result += "^"
    return result

def get_mu_value(match_obj):
    result = "{M}"
    if match_obj.group(1) == "x":
        result += "X"
    else:
        for x in range(0, int(match_obj.group(1))):
            result += "^"
    return result

def get_rc_value(match_obj):
    result = "{R}"
    if match_obj.group(1) == "x":
        result += "X"
    else:
        for x in range(0, int(match_obj.group(1))):
            result += "^"
    return result

def get_number_value(match_obj):
    result = "&"
    if int(match_obj.group(1)) > 10:
        return match_obj.group(1)
    else:
        for x in range(0, int(match_obj.group(1))):
            result += "^"
    return result

def load_file(input_file, output_append):
    f = open(input_file, "r", encoding = "utf8")
    output = json.load(f)
    f.close()
    cards = output["data"]
    cards_edited = cards[:]
    #Removes any cards that are for draft format only. Comment this out if you want to keep them.
    for index, card in enumerate(cards):
        if "text" in card:
            if "Draft format only" in card["text"]:
                cards_edited.remove(card)
    cards = copy.deepcopy(cards_edited)
    for index, card in enumerate(cards):
        for field in card:
            if field in REMOVE:
                cards_edited[index].pop(field)
            else:
                if card[field] == None:
                    cards[index][field] = "none"
                cards_edited[index][field] = str(card[field]).lower()
    cards = copy.deepcopy(cards_edited)
    for index, card in enumerate(cards):
        if "text" not in card:
            cards[index]["text"] = "none"
        if "<ul>" in card["text"]:
            cards[index]["text"] = re.sub("<\/*ul>", "", card["text"])
            cards[index]["text"] = re.sub("<li>", " =", card["text"])
            cards[index]["text"] = re.sub("<\/li>", "", card["text"])
        cards[index]["text"] = re.sub(card["title"], "@", card["text"])
        cards[index]["text"] = re.sub("\n<errata>[^<]+?<\/errata>", "", card["text"])
        cards[index]["text"] = re.sub("<em>[^<]+?<\/em>", "", card["text"])
        cards[index]["text"] = re.sub("<i>[^<]+?<\/i>", "", card["text"])
        cards[index]["text"] = re.sub("<strong>", "", card["text"])
        cards[index]["text"] = re.sub("<\/strong>", "", card["text"])
        cards[index]["text"] = re.sub("interface\s→\s?", "", card["text"])
        cards[index]["text"] = re.sub("<trace>trace\s([0-9]+|x)</trace>", get_trace_value, card["text"])
        cards[index]["text"] = re.sub("trace\[([0-9]+|x)\]", get_trace_value, card["text"])
        cards[index]["text"] = re.sub("([0-9]|x)+\[credit]", get_credit_value, card["text"])
        cards[index]["text"] = re.sub("\[click]", "{O}", card["text"])
        cards[index]["text"] = re.sub("\[trash]", "{T}", card["text"])
        cards[index]["text"] = re.sub("([0-9]+)\[link]", get_link_value, card["text"])
        cards[index]["text"] = re.sub("\[link]", "{L}", card["text"])
        cards[index]["text"] = re.sub("([0-9]+|x)\[mu]", get_mu_value, card["text"])
        cards[index]["text"] = re.sub("\[interrupt]\s→\s?", "", card["text"])
        cards[index]["text"] = re.sub("\[subroutine]", ">", card["text"])
        cards[index]["text"] = re.sub("([0-9]+|x)\[recurring-credit]", get_rc_value, card["text"])
        cards[index]["text"] = re.sub("persistent\s→\s?", "", card["text"])
        cards[index]["text"] = re.sub("access\s→\s?", "", card["text"])
        cards[index]["text"] = card["text"].replace('\n', "\\")
        cards[index]["text"] = re.sub("([0-9]+)", get_number_value, card["text"])
        cards[index]["text"] = re.sub(" one ", " &^ ", card["text"])
        cards[index]["text"] = re.sub(" two ", " &^^ ", card["text"])
        cards[index]["text"] = re.sub(" three ", " &^^^ ", card["text"])
        cards[index]["text"] = re.sub(" four ", " &^^^^ ", card["text"])
        cards[index]["text"] = re.sub(" five ", " &^^^^^ ", card["text"])
        cards[index]["text"] = re.sub(" six ", " &^^^^^^ ", card["text"])
        cards[index]["text"] = re.sub(" seven ", " &^^^^^^^ ", card["text"])
        cards[index]["text"] = re.sub(" eight ", " &^^^^^^^^ ", card["text"])
        cards[index]["text"] = re.sub(" nine ", " &^^^^^^^^^ ", card["text"])
        
        if "influence_limit" in card:
            if card["influence_limit"] != "none":
                influence_limit = int(card["influence_limit"])
                cards[index]["influence_limit"] = "&"
                for x in range(0, influence_limit):
                    cards[index]["influence_limit"] += "^"
        else:
            cards[index]["influence_limit"] = "none"
        
        if "faction_cost" in card:
            faction_cost = int(card["faction_cost"])
            cards[index]["faction_cost"] = "&"
            for x in range(0, faction_cost):
                cards[index]["faction_cost"] += "^"
        else:
            cards[index]["faction_cost"] = "none"
            
        if "cost" in card:
            if card["cost"] == "none":
                cards[index]["cost"] = "X"
                cards[index]["text"] = re.sub("\sx\s", " X ", card["text"])
            try:
                cost = int(card["cost"])
                cards[index]["cost"] = "&"
                for x in range(0, cost):
                    cards[index]["cost"] += "^"
            except:
                pass
        else:
            cards[index]["cost"] = "none"
            
        if "base_link" in card:
            base_link = int(card["base_link"])
            cards[index]["base_link"] = "&"
            for x in range(0, base_link):
                cards[index]["base_link"] += "^"
        else:
            cards[index]["base_link"] = "none"
            
        if "memory_cost" in card:
            memory_cost = int(card["memory_cost"])
            cards[index]["memory_cost"] = "&"
            for x in range(0, memory_cost):
                cards[index]["memory_cost"] += "^"
        else:
            cards[index]["memory_cost"] = "none"
            
        if "strength" in card:
            if card["strength"] == "none":
                cards[index]["strength"] = "X"
                cards[index]["text"] = re.sub("\sx\s", " X ", card["text"])
            try:
                strength = int(card["strength"])
                cards[index]["strength"] = "&"
                for x in range(0, strength):
                    cards[index]["strength"] += "^"
            except:
                pass
        else:
            cards[index]["strength"] = "none"
            
        if "advancement_cost" in card:
            advancement_cost = int(card["advancement_cost"])
            cards[index]["advancement_cost"] = "&"
            for x in range(0, advancement_cost):
                cards[index]["advancement_cost"] += "^"
        else:
            cards[index]["advancement_cost"] = "none"
            
        if "agenda_points" in card:
            agenda_points = int(card["agenda_points"])
            cards[index]["agenda_points"] = "&"
            for x in range(0, agenda_points):
                cards[index]["agenda_points"] += "^"
        else:
            cards[index]["agenda_points"] = "none"
            
        if "trash_cost" in card:
            trash_cost = int(card["trash_cost"])
            cards[index]["trash_cost"] = "&"
            for x in range(0, trash_cost):
                cards[index]["trash_cost"] += "^"
        else:
            cards[index]["trash_cost"] = "none"
            
        if "keywords" in card:
            cards[index]["keywords"] = card["keywords"].split(" - ")
            cards[index]["keywords"] = ", ".join(cards[index]["keywords"])
        else:
            cards[index]["keywords"] = "none"
            
        if "minimum_deck_size" not in card:
            cards[index]["minimum_deck_size"] = "none"
            
        if card["faction_code"] == "neutral-corp" or card["faction_code"] == "neutral-runner":
            cards[index]["faction_code"] = "neutral"
        elif card["faction_code"] == "weyland-consortium":
            cards[index]["faction_code"] = "weyland"
        elif card["faction_code"] == "haas-bioroid":
            cards[index]["faction_code"] = "hb"
        elif card["faction_code"] == "sunny-lebeau":
            cards[index]["faction_code"] = "sunny"
            
        cards[index]["uniqueness"] = str(cards[index]["uniqueness"])
            
    corp = []
    runner = []
    for card in cards:
        if card["side_code"] == "corp":
            corp.append(card)
        elif card["side_code"] == "runner":
            runner.append(card)
    with open(f"corp{output_append}.txt", "w", encoding="utf-8") as f:
        for card in corp:
            for field in CORP_SIDE:
                f.write("|" + field[0])
                if card[field[1]] != "none" and card[field[1]] != "false":
                    f.write(card[field[1]])
            f.write("|\n\n")
        print(f"Corp cards written to corp{output_append}.txt")
    with open(f"runner{output_append}.txt", "w", encoding="utf-8") as f:
        for card in runner:
            for field in RUNNER_SIDE:
                f.write("|" + field[0])
                if card[field[1]] != "none" and card[field[1]] != "false":
                    f.write(card[field[1]])
            f.write("|\n\n")
        print(f"Runner cards written to runner{output_append}.txt")    

argv = sys.argv[1:]
opts, args = getopt.getopt(argv, "i:o:", ["input=", "output="])
input_file = None
output_append = None
print("Processing Cards...")
for opt, arg in opts:
    if opt in ['-i', '--input']:
        input_file = arg
        if input_file[-4:] != "json":
            print("Input must be a JSON file. Please use --input to specify")
            quit()
    elif opt in ['-o', '--output']:
        output_append = arg
if input_file == None:
    input_file = "cards.json"
if output_append == None:
    output_append = "_processed"
load_file(input_file, output_append)
