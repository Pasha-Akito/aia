# Ollama Assistant
* This is an application to quickly have access to a local ollama model via the terminal
* I should be able to ask a question by writing a specifically command such as "aia <my-question>"  (ai assisstant = aia)
* The program should be able to load the local model just for my question and then deload it once I get a response
* I mostly want to just ask a single question at a time, maybe - what is this command do? how do I install something
* * This acts as a quick way to ask a question if I am trying to troubleshoot
* * I have thought about making something to keep track of chats, but I would ask ChatGpt directly for long form conversations so the focus is just on asking a troubleshooting question quickly

# Requirements
This should be as easy as possible to use meaning
* We need a setup command = aia setup
* We need a config command = aia config
* We need a default command = aia <message>

## Setup
* setup command downloads a model of choice
* It should return a list of models depending on the users max VRAM
* Lets say I have 8GB VRAM, I use 2GB normally, so I have only 6GB free. The setup command should know to only show models under 6GB VRAM usage
* We should take the most popular models from hugging tree under 6GB
* We should show the top 10 models they don't have installed
* allow them to pick from 0-9
* Model is downloaded

## Config
* Allows us to switch between models downloaded from Setup and have that as our model going forward

## Default
* Sents the message to the chosen model in the config and returns a response

# Technology
* System service to keep track of aia in terminal
* Python App to startup and close after each command
* Ollama to support the model access

# Acceptance Criteria

- Given a configured model, running `aia What does the ls command do?` returns an answer in the terminal.
- The command exits after returning the response.
- The model is unloaded from memory after the response.
- `aia setup` allows the user to select and download a compatible model.
- `aia config` allows the user to change the default model.
- Subsequent questions use the newly selected model.
