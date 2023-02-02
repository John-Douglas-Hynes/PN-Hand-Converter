import re
import string
import logging
import argparse
#To do: command line interface stuff to get the path file. For now I'll just hard code it.

filePath = "/home/johnhynes/repos/pyfiles/PokerData/pn_2023-01-29p2.csv"

with open(filePath, 'r', encoding='utf-8') as f:
    fileLines=f.readlines()
hands = []
readLine = False
for line in reversed(fileLines):
    initialDataMatch = re.search(r'^"(.*?)"', line)
    initialData = initialDataMatch.group(0) if initialDataMatch else ''
    stringContentMatch = re.search('".*"', line)
    stringContent = stringContentMatch.group(0) if stringContentMatch else ''
    dateStamp = line[stringContentMatch.end()+1:stringContentMatch.end()+11] if stringContentMatch else ''
    timeStamp = line[stringContentMatch.end()+12:stringContentMatch.end()+20] if stringContentMatch else ''
    if "starting hand" in initialData:
        hand = []
        readLine = True
    if readLine: hand.append(stringContent)
    if "ending hand" in initialData:
        hand.append(stringContent) 
        readLine = False
        hands.append((hand, dateStamp, timeStamp))

def handIdHash(handId):
    if handId == 0:
        raise ValueError('invalid handId')
    val = 0
    for i, c in enumerate(handId):
        if c in string.digits:
            val += int(c)*36**i
        else:
            val += (10+string.ascii_lowercase.index(c))*36**i
    return val

def getPlayerId(string):
    playerIds = re.findall('(?<=@ )[0-9a-zA-Z\-]{10}(?="")', string) #since people can technically call themselves @ aaaaaaaaaa"" we have to find the last pattern of this form
    return playerIds[-1]

def makePlayerDict(line):
    playerList = re.findall('#[0-9]*?.*?@ [0-9a-zA-Z\-]{10}"" \([0-9]*\)(?= \||"$)', line) #since player names are limited to 15 characters, there's no hacking this
    playerDict = {}
    for player in playerList:
        seatIdMatch = re.search('(?<=#)[0-9]*', player)
        seatId = int(seatIdMatch.group(0))
        aliasMatch = re.search('(?<="").*?(?= @ [0-9a-zA-Z\-]{10}"")', player)
        alias = aliasMatch.group(0)
        playerId = getPlayerId(player)
        stackMatch = re.findall('(?<=\()[0-9]*(?=\))', player) #same as above - must find last to avoid name trickery
        stack = int(stackMatch[-1])
        playerDict[playerId] = (seatId,alias,stack)
    return playerDict

def getPreamble(hand):
    handDataMatch = re.search('(?<=\(id: )[a-z0-9]{9}', hand[0])
    handData = handDataMatch.group(0) if handDataMatch else None
    handId = handIdHash(handData)
    gameTypeMatch = re.search('(?<=\()[a-zA-Z\s\']*(?=\))', hand[0])
    gameType = gameTypeMatch.group(0) if gameTypeMatch else ''
    dealerMatch = re.search('(?<=\(dealer: ).*(?=\))', hand[0])
    dealerId = getPlayerId(hand[0]) if dealerMatch else None
    sbPosterIds = []
    bbPosterIds = []
    for line in hand:
        if re.search('^"Player stacks', line):
            playerDict = makePlayerDict(line)
        bbMatch = re.search('(?<=big blind of )[0-9](?="$)', line)
        if bbMatch:
            bb = int(bbMatch.group(0))
            bbPosterIds.append(getPlayerId(line))
        sbMatch = re.search('(?<=small blind of )[0-9](?="$)', line)
        if sbMatch:
            sb = int(sbMatch.group(0))
            sbPosterIds.append(getPlayerId(line))
    return [handData, handId, gameType, dealerId, sb, sbPosterIds, bb, bbPosterIds, playerDict]

def getPreflop(hand):
    preflop = []
    readLines = True
    for line in hand:
        actionMatch = re.search('(?<=@ [0-9a-zA-Z\-]{10}"") (folds|checks|calls|bets|raises)', line)
        if actionMatch and readLines:
            playerId = getPlayerId(line)
            actionText = line[actionMatch.start():]
            preflop.append((playerId, actionText))
        flopMatch = re.search('^"Flop:', line)
        if flopMatch:
            readLines = False
    return preflop

def replaceSuits(string):
    dic = {'♣': 'c', '♠': 's', '♥': 'h', '♦':'d'}
    replacementString = string
    for i, j in dic.items():
        replacementString = replacementString.replace(i, j)
    return replacementString

def getFlop(hand):
    flop = None
    flopActions = []
    readLines = False
    for line in hand:
        flopMatch = re.search('^"Flop:', line)
        if flopMatch:
            readLines = True
            flop = replaceSuits(line[1:-1].replace('Flop:', '*** FLOP ***'))
            flop = flop.replace(',', '')
        actionMatch = re.search('(?<=@ [0-9a-zA-Z\-]{10}"") (folds|checks|calls|bets|raises)', line)
        if actionMatch and readLines:
            playerId = getPlayerId(line)
            actionText = line[actionMatch.start():]
            flopActions.append((playerId, actionText))
        turnMatch = re.search('^"Turn:', line)
        if turnMatch:
            readLines = False
    return [flop, flopActions]

def getTurn(hand):
    turn = None
    turnActions = []
    readLines = False
    for line in hand:
        turnMatch = re.search('^"Turn:', line)
        if turnMatch:
            readLines = True
            turn = replaceSuits(line[1:-1].replace('Turn: ', '*** TURN *** ['))
            turn = turn.replace(turn[-5:], ']'+turn[-5:])
            turn = turn.replace(',', '')
        actionMatch = re.search('(?<=@ [0-9a-zA-Z\-]{10}"") (folds|checks|calls|bets|raises)', line)
        if actionMatch and readLines:
            playerId = getPlayerId(line)
            actionText = line[actionMatch.start():]
            turnActions.append((playerId, actionText))
        riverMatch = re.search('^"River:', line)
        if riverMatch:
            readLines = False
    return [turn, turnActions]

def getRiver(hand):
    river = None
    riverActions = []
    readLines = False
    for line in hand:
        riverMatch = re.search('^"River:', line)
        if riverMatch:
            readLines = True
            river = replaceSuits(line[1:-1].replace('River: ', '*** RIVER *** ['))
            river = river.replace(river[-5:], ']'+river[-5:])
            river = river.replace(',', '')
        actionMatch = re.search('(?<=@ [0-9a-zA-Z\-.]{10}"") (folds|checks|calls|bets|raises)', line)
        if actionMatch and readLines:
            playerId = getPlayerId(line)
            actionText = line[actionMatch.start():]
            riverActions.append((playerId, actionText))
    return [river, riverActions]

def getUncalledBet(hand):
    uncalled = []
    for line in hand:
        uncalledMatch = re.search('^"Uncalled bet', line)
        if uncalledMatch:
            playerId = getPlayerId(line)
            lineText = line[:line.index('""')]
            uncalled.append((playerId, lineText))
    return uncalled

def getShowDown(hand):
    showDown = []
    for line in hand:
        collectedMatch = re.search('collected [0-9.]* from pot with', line)
        if collectedMatch:
            playerId = getPlayerId(line)
            playernameIndex = len(line) - line[::-1].index('""')
            withIndex = line.index('with')
            lineText = line[playernameIndex:withIndex]
            potSize = re.search('(?<=collected )[0-9]*', lineText)
            showDown.append((playerId,lineText, potSize.group(0)))
        showMatch = re.search('"" shows a ', line)
        if showMatch:
            playerId = getPlayerId(line)
            playernameIndex = len(line) - line[::-1].index('""')
            lineText = line[playernameIndex:]
            lineText = replaceSuits(lineText.replace('a ', '['))
            lineText = lineText.replace('.', ']')
            lineText = lineText.replace(',', '')
            showDown.append((playerId,lineText))
    return showDown

def getPostamble(hand):
    postamble = []
    for line in hand:
        collectedMatch = re.search('collected [0-9.]* from pot(?="$)', line)
        if collectedMatch:
            playerId = getPlayerId(line)
            playernameIndex = len(line) - line[::-1].index('""')
            lineText = line[playernameIndex:]
            potSize = re.search('(?<=collected )[0-9]*', lineText)
            postamble.append((playerId,lineText, potSize.group(0)))
    return postamble

def getSummaryText(playerId, activeOnFlop, activeOnTurn, activeOnRiver, handWinner):
    if playerId not in activeOnFlop:
        return 'folded before the Flop'
    elif playerId not in activeOnTurn:
        return 'folded on the Flop'
    elif playerId not in activeOnRiver:
        return 'folded on the River'
    elif playerId != handWinner:
        return 'mucked'
    elif playerId == handWinner:
        return 'won'
    else:
        return 'is sitting out'

def makePSHH(hand):
    preamble = getPreamble(hand[0])
    playerDict = preamble[-1]
    handOverview = f"""PokerStars Hand #{preamble[1]}: {preamble[2]} ({preamble[4]}/{preamble[6]}) - {hand[1]} {hand[2]} GMT 
Table 'Pokernowclub' 10-max (Play money) seat #{playerDict[preamble[3]][0]} is the button\n"""
    seatinfo = ''.join(f'seat {tup[0]}: {tup[1]} ({tup[2]} in chips)\n' for tup in list(playerDict.values()))
    smallBlinds = ''.join(f'{playerDict[playerId][1]} post small blind {preamble[4]}\n' for playerId in preamble[5])
    bigBlinds = ''.join(f'{playerDict[playerId][1]} post big blind {preamble[6]}\n' for playerId in preamble[7])
    preflop = getPreflop(hand[0])
    preflopText = '*** HOLE CARDS ***\n' + '\n'.join(f'{playerDict[line[0]][1]}{line[1][:-1]}' for line in preflop)
    returnText = handOverview+seatinfo+smallBlinds+bigBlinds+preflopText
    playersActiveOnFlop = playersActiveOnTurn = playersActiveOnRiver = set()
    allFlop = getFlop(hand[0])
    if allFlop[0] is not None:
        returnText += '\n' + allFlop[0] + '\n' + '\n'.join(f'{playerDict[line[0]][1]}{line[1][:-1]}' for line in allFlop[1])
        playersActiveOnFlop = set(action[0] for action in allFlop[1])
    allTurn = getTurn(hand[0])
    if allTurn[0] is not None:
        returnText += '\n' + allTurn[0] + '\n' + '\n'.join(f'{playerDict[line[0]][1]}{line[1][:-1]}' for line in allTurn[1])
        playersActiveOnTurn = set(action[0] for action in allTurn[1])
    allRiver = getRiver(hand[0])
    if allRiver[0] is not None:
        returnText += '\n' + allRiver[0] + '\n' + '\n'.join(f'{playerDict[line[0]][1]}{line[1][:-1]}' for line in allRiver[1])
        playersActiveOnRiver = set(action[0] for action in allRiver[1])
    uncalled = getUncalledBet(hand[0])
    if uncalled != []:
        returnText += '\n' + '\n'.join(line[1][1:-1]+f' {playerDict[line[0]][1]}' for line in uncalled)
    post = getPostamble(hand[0])
    returnText += '\n' + '\n'.join(f'{playerDict[line[0]][1]} '+line[1][1:-1] for line in post)
    showdownText = '*** SHOW DOWN ***'
    showDown = getShowDown(hand[0])
    if showDown != []:
        returnText += showdownText
        returnText += '\n' + '\n'.join(f'{playerDict[line[0]][1]} '+line[1][1:-1] for line in showDown)
    summaryText = '\n*** SUMMARY ***\n'
    handWinner = None
    for line in showDown:
        if len(line) > 2:
            pot = line[2]
            handWinner = line[0]
    for line in post:
        if len(line) > 2:
            pot = line[2]
            handWinner = line[0]
    summaryText += f'Total pot {pot} | Rake 0\n'
    for playerId in list(playerDict.keys()):
        summaryText += f'seat {playerDict[playerId][0]}: {playerDict[playerId][1]} {getSummaryText(playerId, playersActiveOnFlop, playersActiveOnTurn, playersActiveOnRiver, handWinner)}\n'
    returnText += summaryText
    return returnText

if __name__=="__main__":
    for hand in hands:
        try:
            print(makePSHH(hand))
        except:
            print('Error processing hand')
