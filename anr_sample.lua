-- https://drive.google.com/file/d/0BxF7G2b8kigCYnpERFNpR2I3cjQ/view?usp=sharing
-- modifications by Talcos allow 'whispering' to prime the network

--[[

This file samples characters from a trained model

Code is based on implementation in 
https://github.com/oxford-cs-ml-2015/practical6

]]--

require 'torch'
require 'nn'
require 'nngraph'
require 'optim'
require 'lfs'

require 'util.OneHot'
require 'util.misc'
require 'model.LSTMb'

cmd = torch.CmdLine()
cmd:text()
cmd:text('Sample from a character-level language model')
cmd:text()
cmd:text('Options')
-- required:
cmd:argument('-model','model checkpoint to use for sampling')
-- optional parameters
cmd:option('-seed',123,'random number generator\'s seed')
cmd:option('-sample',1,' 0 to use max at each timestep, 1 to sample at each timestep')
cmd:option('-primetext',"",'used as a prompt to "seed" the state of the LSTM using a given sequence, before we sample.')
cmd:option('-length',2000,'number of characters to sample')
cmd:option('-temperature',0.8,'temperature of sampling')
cmd:option('-gpuid',-1,'which gpu to use. -1 = use CPU')
cmd:option('-verbose',0,'set to 1 to print diagnostics before the sampled cards.')
cmd:option('-cardtype',"",'added the start of the type section.')
cmd:option('-keywords',"",'added to the start of the keywords section.')
cmd:option('-faction',"",'added to the start of the faction section.')
cmd:option('-influence',"",'added to the start of the influence section.')
cmd:option('-strength',"",'added to the start of the strength section.')
cmd:option('-uniqueness',"",'added to the start of the uniqueness section')
cmd:option('-advancementcost_baselink',"",'added to the start of the advancement cost section for corp cards, or base link section for runner cards.')
cmd:option('-agendapoints_memorycost',"",'added to the start of the agenda points section for corp cards or the memory cost section for runner cards.')
cmd:option('-influencelimit',"",'added to the start of the influence limit section.')
cmd:option('-decksize',"",'added to the end of the deck size section.')
cmd:option('-text',"",'added to the end of the text section.')
cmd:option('-cost',"",'added to the end of the cost section.')
cmd:option('-title',"",'added to the start of the title section')
cmd:option('-trashcost',"",'added to the start of the trash cost section')
cmd:option('-side',"corp",'generate runner cards or corp cards?')

cmd:text()

-- parse input params
opt = cmd:parse(arg)

-- gated print: simple utility function wrapping a print
function gprint(str)
    if opt.verbose == 1 then print(str) end
end

-- check that cunn/cutorch are installed if user wants to use the GPU
if opt.gpuid >= 0 then
    local ok, cunn = pcall(require, 'cunn')
    local ok2, cutorch = pcall(require, 'cutorch')
    if not ok then gprint('package cunn not found!') end
    if not ok2 then gprint('package cutorch not found!') end
    if ok and ok2 then
        gprint('using CUDA on GPU ' .. opt.gpuid .. '...')
        cutorch.setDevice(opt.gpuid + 1) -- note +1 to make it 0 indexed! sigh lua
        cutorch.manualSeed(opt.seed)
    else
        gprint('Falling back on CPU mode')
        opt.gpuid = -1 -- overwrite user setting
    end
end
torch.manualSeed(opt.seed)

-- load the model checkpoint
if not lfs.attributes(opt.model, 'mode') then
    gprint('Error: File ' .. opt.model .. ' does not exist. Are you sure you didn\'t forget to prepend cv/ ?')
end
checkpoint = torch.load(opt.model)
protos = checkpoint.protos
protos.rnn:evaluate() -- put in eval mode so that dropout works properly

-- initialize the vocabulary (and its inverted version)
local vocab = checkpoint.vocab
local ivocab = {}
for c,i in pairs(vocab) do ivocab[i] = c end

-- initialize the rnn state to all zeros
gprint('creating an LSTM...')
local current_state
local num_layers = checkpoint.opt.num_layers
current_state = {}
for L = 1,checkpoint.opt.num_layers do
    -- c and h for all layers
    local h_init = torch.zeros(1, checkpoint.opt.rnn_size)
    if opt.gpuid >= 0 then h_init = h_init:cuda() end
    table.insert(current_state, h_init:clone())
    table.insert(current_state, h_init:clone())
end
state_size = #current_state

-- do a few seeded timesteps
local seed_text = opt.primetext
if string.len(seed_text) > 0 then
    gprint('seeding with ' .. seed_text)
    gprint('--------------------------')
    for c in seed_text:gmatch'.' do
        prev_char = torch.Tensor{vocab[c]}
        io.write(ivocab[prev_char[1]])
        if opt.gpuid >= 0 then prev_char = prev_char:cuda() end
        local lst = protos.rnn:forward{prev_char, unpack(current_state)}
        -- lst is a list of [state1,state2,..stateN,output]. We want everything but last piece
        current_state = {}
        for i=1,state_size do table.insert(current_state, lst[i]) end
        prediction = lst[#lst] -- last element holds the log probabilities
    end
else
    -- fill with uniform probabilities over characters (? hmm)
    gprint('missing seed text, using uniform probability over first character')
    gprint('--------------------------')
    prediction = torch.Tensor(1, #ivocab):fill(1)/(#ivocab)
    if opt.gpuid >= 0 then prediction = prediction:cuda() end
end

-- start sampling/argmaxing

local barcount = 0

for i=1, opt.length do 

    -- log probabilities from the previous timestep
    if opt.sample == 0 then
        -- use argmax
        local _, prev_char_ = prediction:max(2)
        prev_char = prev_char_:resize(1)
    else
        -- use sampling
        prediction:div(opt.temperature) -- scale by temperature
        local probs = torch.exp(prediction):squeeze()
        probs:div(torch.sum(probs)) -- renormalize so probs sum to one
        prev_char = torch.multinomial(probs:float(), 1):resize(1):float()
    end

    -- forward the rnn for next character
    local lst = protos.rnn:forward{prev_char, unpack(current_state)}
    
    if not (string.len(opt.text) > 0 and ivocab[prev_char[1]] == '|') then 
    	current_state = {}
    	for i=1,state_size do table.insert(current_state, lst[i]) end
    end

    prediction = lst[#lst] -- last element holds the log probabilities


    local prependtext = ""

    if ivocab[prev_char[1]] == '\n' then
	barcount = 0
    end

    if ivocab[prev_char[1]] == '|' then
	barcount = barcount + 1
    end
    
    if not (string.len(opt.text) > 0 and ivocab[prev_char[1]] == '|') then 
    	io.write(ivocab[prev_char[1]])
    end

    if ivocab[prev_char[1]] == '|' then
    if barcount == 1 then
    	if type(tonumber(opt.cardtype)) == "number" then
    		x = tonumber(opt.cardtype)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.cardtype = newstring
    	end
	prependtext = "1" .. opt.cardtype:lower()
    elseif barcount == 2 then
    	if type(tonumber(opt.keywords)) == "number" then
    		x = tonumber(opt.keywords)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.keywords = newstring
    	end
	prependtext = "2" .. opt.keywords:lower()
    elseif barcount == 3 then
    	if type(tonumber(opt.faction)) == "number" then
    		x = tonumber(opt.faction)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.faction = newstring
    	end
	prependtext = "3" .. opt.faction:lower()
    elseif barcount == 4 then
    	if type(tonumber(opt.influence)) == "number" then
    		x = tonumber(opt.influence)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.influence = newstring
    	end
	prependtext = "4" .. opt.influence:lower()
    elseif barcount == 5 then
    	if type(tonumber(opt.strength)) == "number" then
    		x = tonumber(opt.strength)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.strength = newstring
    	end
	prependtext = "5" .. opt.strength:lower()
    elseif barcount == 6 then
    	if type(tonumber(opt.uniqueness)) == "number" then
    		x = tonumber(opt.uniqueness)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.uniqueness = newstring
    	end
	prependtext = "6" .. opt.uniqueness:lower()
    elseif barcount == 7 then
    	if type(tonumber(opt.advancementcost_baselink)) == "number" then
    		x = tonumber(opt.advancementcost_baselink)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.advancementcost_baselink = newstring
    	end
	prependtext = "7" .. opt.advancementcost_baselink:lower()
    elseif barcount == 8 then
    	if type(tonumber(opt.agendapoints_memorycost)) == "number" then
    		x = tonumber(opt.agendapoints_memorycost)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.agendapoints_memorycost = newstring
    	end
	prependtext = "8" .. opt.agendapoints_memorycost:lower()
    elseif barcount == 9 then
    	if type(tonumber(opt.influencelimit)) == "number" then
    		x = tonumber(opt.influencelimit)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.influencelimit = newstring
    	end
	prependtext = "9" .. opt.influencelimit:lower()
    elseif barcount == 10 then
    	if type(tonumber(opt.decksize)) == "number" then
    		x = tonumber(opt.decksize)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.decksize = newstring
    	end
	prependtext = "10" .. opt.decksize:lower()
    elseif barcount == 11 then
    	if type(tonumber(opt.text)) == "number" then
    		x = tonumber(opt.text)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.text = newstring
    	end
	prependtext = "11" .. opt.text:lower()
    elseif barcount == 12 then
    	if type(tonumber(opt.cost)) == "number" then
    		x = tonumber(opt.cost)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.cost = newstring
    	end
	prependtext = "12" .. opt.cost:lower()
    elseif barcount == 13 then
    	if type(tonumber(opt.title)) == "number" then
    		x = tonumber(opt.title)
    		newstring = "&"
    		for i=0,x do
    			if i ~= 0 then
    				newstring = newstring .. "^"
    			end
    		end
    		opt.title = newstring
    	end
	prependtext = "13" .. opt.title:lower()
    elseif opt.side == "corp" then
    	if barcount == 14 then
    		if type(tonumber(opt.trashcost)) == "number" then
    			x = tonumber(opt.trashcost)
    			newstring = "&"
    			for i=0,x do
    				if i ~= 0 then
    					newstring = newstring .. "^"
    				end
    			end
    			opt.trashcost = newstring
    		end
		prependtext = "14" .. opt.trashcost:lower()
    	end
    end	
    end



    if string.len(prependtext) > 0 then
    		for c in prependtext:gmatch'.' do
        		local prev_char_test = torch.Tensor{vocab[c]}
        		io.write(ivocab[prev_char_test[1]])
        		if opt.gpuid >= 0 then prev_char_test = prev_char_test:cuda() end
        		local lst_test = protos.rnn:forward{prev_char_test, unpack(current_state)}
        		prediction = lst_test[#lst_test] -- last element holds the log probabilities
		end
    end




end
io.write('\n') io.flush()
