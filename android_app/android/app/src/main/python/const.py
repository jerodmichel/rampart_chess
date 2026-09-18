#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 11:37:10 2024

@author: stereo
"""

# ░█████╗░░█████╗░███╗░░██╗░██████╗████████╗░█████╗░███╗░░██╗████████╗░██████╗
# ██╔══██╗██╔══██╗████╗░██║██╔════╝╚══██╔══╝██╔══██╗████╗░██║╚══██╔══╝██╔════╝
# ██║░░╚═╝██║░░██║██╔██╗██║╚█████╗░░░░██║░░░███████║██╔██╗██║░░░██║░░░╚█████╗░
# ██║░░██╗██║░░██║██║╚████║░╚═══██╗░░░██║░░░██╔══██║██║╚████║░░░██║░░░░╚═══██╗
# ╚█████╔╝╚█████╔╝██║░╚███║██████╔╝░░░██║░░░██║░░██║██║░╚███║░░░██║░░░██████╔╝
# ░╚════╝░░╚════╝░╚═╝░░╚══╝╚═════╝░░░░╚═╝░░░╚═╝░░╚═╝╚═╝░░╚══╝░░░╚═╝░░░╚═════╝░

# screen dimensions
WIDTH = 800
HEIGHT = 800

# board dimensions
ROWS = 6
COLS = 10

# caps on numbers of raiders/queens
RAIDERS = 8
DEAD_RAIDERS = 5
GRAVES = 9

RWIDTH = WIDTH // COLS
RHEIGHT = HEIGHT // ROWS

RAMPART_HEIGHT = 20

DECK = 13

CEM_HEIGHT = 450

CWIDTH = 90
CHEIGHT = (HEIGHT - CEM_HEIGHT - 10) // DECK

GWIDTH = CWIDTH
GHEIGHT = (CEM_HEIGHT - 150) // GRAVES

SUITS = ["\u2663", "\u2665", "\u2666", "\u2660"]

RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

SQS = [(x,y) for x in range(COLS) for y in range(ROWS)]

CARDSQS = [(x,0) for x in [2,3,4]] + \
              [(x,1) for x in range(COLS) if x % 2 == 0] + \
              [(x,2) for x in range(COLS) if x % 2 == 1] + \
              [(x,3) for x in range(COLS) if x % 2 == 0] + \
              [(x,4) for x in range(COLS) if x % 2 == 1] + \
              [(x,5) for x in [5,6,7]]
              
TABLE = []
for (x,y) in SQS:
    if (x,y) in CARDSQS:
        if y == 0:
            if x not in [2,3,4]:
                TABLE.append((x,y,'',''))
            elif x == 2:
                TABLE.append((x,y,RANKS[12],SUITS[1]))
            elif x == 3:
                TABLE.append((x,y,RANKS[11],SUITS[1]))
            elif x == 4:
                TABLE.append((x,y,RANKS[10],SUITS[1]))
        elif y in [1,2]:
            TABLE.append((x,y,RANKS[x],SUITS[1]))
        elif y in [3,4]:
            TABLE.append((x,y,RANKS[COLS-x-1],SUITS[2]))
        elif y == 5:
            if x not in [5,6,7]:
                TABLE.append((x,y,'',''))
            elif x == 5:
                TABLE.append((x,y,RANKS[10],SUITS[2]))
            elif x == 6:
                TABLE.append((x,y,RANKS[11],SUITS[2]))
            elif x == 7:
                TABLE.append((x,y,RANKS[12],SUITS[2]))
                
TABLE_DICT = {}
for (x,y) in SQS:
    if (x,y) in CARDSQS:
        if y == 0:
            if x not in [2,3,4]:
                TABLE_DICT.update({(x,y) : ('','')})
            elif x == 2:
                TABLE_DICT.update({(x,y) : (12,3)})
            elif x == 3:
                TABLE_DICT.update({(x,y) : (11,3)})
            elif x == 4:
                TABLE_DICT.update({(x,y) : (10,3)})
        elif y in [1,2]:
            TABLE_DICT.update({(x,y) : (x,3)})
        elif y in [3,4]:
            TABLE_DICT.update({(x,y) : (COLS-x-1,2)})
        elif y == 5:
            if x not in [5,6,7]:
                TABLE_DICT.update({(x,y) : ('','')})
            elif x == 5:
                TABLE_DICT.update({(x,y) : (10,2)})
            elif x == 6:
                TABLE_DICT.update({(x,y) : (11,2)})
            elif x == 7:
                TABLE_DICT.update({(x,y) : (12,2)})
                
#print(TABLE_DICT)
                
REV_TAB_DICT = {}
for (x,y) in SQS:
    if (x,y) in CARDSQS:
        if y == 0:
            if x == 2:
                REV_TAB_DICT.update({(12,3) : (x,y)})
            elif x == 3:
                REV_TAB_DICT.update({(11,3) : (x,y)})
            elif x == 4:
                REV_TAB_DICT.update({(10,3) : (x,y)})
        elif y in [1,2]:
            REV_TAB_DICT.update({(x,3) : (x,y)})
        elif y in [3,4]:
            REV_TAB_DICT.update({(COLS-x-1,2) : (x,y)})
        elif y == 5:
            if x == 5:
                REV_TAB_DICT.update({(10,2) : (x,y)})
            elif x == 6:
                REV_TAB_DICT.update({(11,2) : (x,y)})
            elif x == 7:
                REV_TAB_DICT.update({(12,2) : (x,y)})
                
CARD_VAL = {0 : 1, 1 : 2, 2 : 3, 3 : 4, 4 : 5, 5 : 6, 6 : 7, 7 : 8, 8 : 9, 9 : 10, \
               10 : 10, 11 : 10, 12 : 10}
                

DECK_SQS = [(x,y) for x in range(2) for y in range(DECK)]


DECK_TABLE = []
for x in range(2):
    for y in range(DECK):
        DECK_TABLE.append((x,y,RANKS[y],SUITS[x])) if x == 0 else \
            DECK_TABLE.append((x,y,RANKS[y],SUITS[x+2]))
            

GRAVEYARD = [(x,y) for x in range(2) for y in range(GRAVES)]

CASTBUTTONS = [0, 1]
                

print("CARD_VAL mappings:", CARD_VAL)           
                


