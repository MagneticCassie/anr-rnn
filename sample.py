import subprocess
import random
import sys
import getopt

arguments = {"script":"anr_sample.lua", "seed":"0", "sample":"1", "primetext":"", "length":"20000", "temperature":"0.8", "gpuid":"-1", "verbose":"0", "cardtype":"", "keywords":"", "faction":"", "influence":"", "strength":"", "uniqueness":"", "advancementcost_baselink":"", "agendapoints_memorycost":"", "influencelimit":"", "decksize":"", "text":"", "cost":"", "title":"", "trashcost":"", "side":"", "checkpoint": "cv/runner/YOURFILEHERE.t7"}

arguments["seed"] = str(random.randint(0, 999999999))

argv = sys.argv[1:]
opts, args = getopt.getopt(argv, "", ["script=", "seed=", "sample=", "primetext=", "length=", "temperature=", "gpuid=", "verbose=", "cardtype=", "keywords=", "faction=", "influence=", "strength=", "uniqueness=", "advancementcost_baselink=", "agendapoints_memorycost=", "influencelimit=", "decksize=", "text=", "cost=", "title=", "trashcost=", "side=", "checkpoint="])

print("-------------------")
print("Generating Cards...")

for opt, arg in opts:
	for argument in arguments:
		if opt in [f"--{argument}"]:
			arguments[argument] = arg
			
command = ['th']
command.append(f"{arguments['script']}")
command.append(f"{arguments['checkpoint']}")
for argument in arguments:
	if arguments[argument] != "" and argument != "script" and argument != "checkpoint":
		command.append(f"-{argument}")
		command.append(arguments[argument])
		
f = open("anrdecode/output.txt", "w")
subprocess.call(command, stdout = f)
f.close()

command = ["python3", "anr_decode.py", "--input", "output.txt", "--side"]
command.append(arguments['side'])
subprocess.call(command, cwd='anrdecode')
