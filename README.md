# Peer-to-Peer Filesharing
This is an example of a P2P network. There is a central server that tracks peers on the network and file replicas, and the Peers communicate with the server and eachother to download files from each other.

## How It's Made:

**Tech used:** Python, Linux

Everything is written in python in an Ubuntu environment.

## Lessons Learned:

- Maintain consistency as much as possible. There are cases where I didn't need to prepend an OPCODE and the program would still function fine, however, I found it was best to add the OPCODE anyway. If you know that every time a message is sent, it has a header and the length of the message is prepended to it, that consistency makes life a lot easier. The process of sending and reading messages can be abstracted with a few functions and your code becomes more modular.
- Simpler is better. Having the server run as a subprocess sounded cool in the beginning, but it created serveral headaches. In hindsight, since this project was never meant to handle a massive load of traffic, I would just run the server in a thread.
- Double your time spent planning and checking your plan before writing the code. I wish I spent more time planning out the functionality and requirements of the project. I jumped into coding too early on, and that created spaghetting code at times. I have spent much more time cleaning up the code and refacotring it that it would have taken me to plan it out more thuroughly.
