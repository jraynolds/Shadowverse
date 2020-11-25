import random
import enum
import importlib
import json
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(THIS_FOLDER, 'cardlibrary.json')) as cardlibrary:
	library = json.load(cardlibrary)

# ENUMS
class CARD_TYPES(enum.Enum):
	"""The different types of cards we can have.
	"""
	monster = 0
	spell = 1
	amulet = 2

class DEBUG_STATES(enum.IntEnum):
	"""Debug states to be toggled on and off for output to the console.
	"""
	basics = 0
	triggers = 1
	playability = 2
	effects = 3
	targets = 4
	resources = 5
	expandedInfo = 6
	kwargs = 7
	playerInput = 8
	errors = 9
	interactions = 10

"""A list of booleans describing what level of debug data is output to the console. By default "basics" is enabled.
"""
ACTIVE_DEBUG_STATES = [ False for state in DEBUG_STATES ]
ACTIVE_DEBUG_STATES[DEBUG_STATES.basics] = True
ACTIVE_DEBUG_STATES[DEBUG_STATES.errors] = True
ACTIVE_DEBUG_STATES[DEBUG_STATES.interactions] = True

class ATTACK_STATES(enum.Enum):
	"""The different attack states a monster card can be in. Usually "sickness" on play, and "storm" thereafter. Changes to "attacked" after attacking once. "Rush" can attack enemy creatures but not the enemy player, while "Storm" can do both.
	"""
	sickness = 0
	rush = 1
	storm = 2
	attacked = 3
	
class CARD_STATES(enum.IntEnum):
	"""The different card states.
	"""
	inDeck = 0
	held = 1
	played = 2
	evolved = 3
	destroyed = 4
	banished = 5

class CARD_LOCATIONS(enum.Enum):
	"""The different places a card can be.
	"""
	inFriendlyHand = 0
	onFriendlyBoard = 1
	onEnemyBoard = 2
	inFriendlyGraveyard = 3
	inFriendlyDeck = 4

class EFFECT_REGISTRY_TIMES(enum.Enum):
	"""A list of times we register effects on given cards.
	"""
	gameStart = 0
	cardDrawn = 1
	cardPlayed = 2
	monsterEvolved = 3

"""A list of triggers produced outside of a card's object.
"""
globalTriggers = [
	"TurnStart",
	"CardInvoked",
	"CardDrawn",
	"CardDiscarded",
	"CardSummoned",
	"CardPlayed",
	"CardEntersBattlefield",
	"Necromancy",
	"CardAttacking",
	"CardsClashed",
	"CardDestroyed",
	"CardBanished",
	"CardLeavesBattlefield",
	"CardEvolved",
	"Changed",
	"TurnEnd"
]

"""A list of triggers produced inside a card object.
"""
cardTriggers = [
	"Drawn",
	"Summoned",
	"Played",
	"Cast",
	"Accelerated",
	"Enhanced",
	"TargetsChosen",
	"BurialRiter",
	"BurialRitee",
	"EntersBoard",
	"Evolved",
	"Attacking",
	"Clashing",
	"LeaderClashing",
	"DealtDamage",
	"TookDamage",
	"Destroying",
	"Destroyed",
	"Banishing",
	"Banished",
	"LeavesBoard",
	"Discarded"
]
TRIGGER_TYPES = enum.IntEnum("TRIGGER_TYPES", 
	["onFriendly" + i for i in globalTriggers] + 
	["onEnemy" + i for i in globalTriggers] + 
	["on" + i for i in cardTriggers]
)

 # GAME OBJECTS

class Logic:
	"""A logic class to ponder game logic and possible moves. Holds card numbers for quick referencing.
	"""
	def __init__(self):
		"""Initialize and set card number to 0.
		"""
		self.cardNumCounter = 0
		self.cards = []


	def getCard(self, cardNum):
		"""Get a card from a given index number.

		Args:
				cardNum (Integer): index number of the card

		Returns:
				Card: card at that index
		"""
		return self.cards[cardNum]

	def getOwner(self, cardNum):
		"""Get the owner of a given card index.

		Args:
				cardNum (Integer): index number of the card

		Returns:
				Player: the owner of that card index
		"""
		if cardNum in game.players[0].cardNumbers:
			return game.players[0]
		return game.players[1]

	def canPlayCard(self, player, card):
		"""Find whether a given player can play a given card.

		Args:
				player (Player): the player
				card (Card): the card

		Returns:
				Boolean: whether the given player can play the given card.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("Can we play {0}?".format(card.name))
		if card.cost > player.energy:
			if card.isOfType("Monster") and card.accelerate:
				if card.accelerate["Cost"] > player.energy:
					if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("No. It costs too much, even with Accelerate.")
					return False
			else :
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("No. It costs too much.")
				return False

		if card.isOfType("Monster"):
			if not player.board.hasSpace() and not card.accelerate:
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("No. No space on the board.")
				return False
			elif card.accelerate:
				if "Targets" in card.accelerate and len(self.getValidTargets(player, card.accelerate["Targets"])) < 1:
					if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("No. No valid targets.")
					return False
		elif card.isOfType("Amulet"):
			if not player.board.hasSpace():
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("No. No space on the board.")
				return False
		elif card.isOfType("Spell"):
			if card.targets and len(self.getValidTargets(player, card.targets)) < 1:
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("No. No valid targets.")
				return False

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("Yes!")
		return True

	def canAttackWithCard(self, player, card):
		"""Find whether a given player can attack with a given card. Automatically returns false if the card is not a MonsterCard.

		Args:
				player (Player): the player
				card (Card): the card

		Returns:
				Boolean: whether the player can attack with this card.
		"""
		if not isinstance(card, MonsterCard):
			return False
		if card.getAttackState() is ATTACK_STATES.sickness or card.getAttackState() is ATTACK_STATES.attacked:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("Can't attack with {0}. Attackstate is {1}.".format(card.name, card.getAttackState()))
			return False
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playability]: print("{} can attack!.".format(card.name))
		return True


	def getValidTargets(self, owner, targetTypes):
		"""Get a list of the valid targets for a given player and a list of target types.

		Args:
				owner (Player): the player checking for targets
				targetTypes (List(Object)): a list of objects with fields such as "Type", "Location", or an eval, "Test."

		Returns:
				List(Object): a list of objects, including "Card" and "Player."
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print("Getting valid targets.")
		valids = []
		for targetObj in targetTypes:
			potentialValids = game.players[0].board.getCards() + game.players[1].board.getCards() + owner.hand.getCards()
			if "Type" in targetObj:
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print("This target is of type {0}. Valid targets:".format(targetObj["Type"]))
				if targetObj["Type"] == "EnemyPlayer":
					potentialValids = [game.getOtherPlayer(owner)]
				if targetObj["Type"] == "FriendlyPlayer":
					potentialValids = [owner]
				if targetObj["Type"] == "Monster":
					potentialValids = [
						potential for potential in potentialValids 
						if potential.isOfType("Monster")
					]
				if targetObj["Type"] == "Amulet":
					potentialValids = [
						potential for potential in potentialValids 
						if potential.isOfType("Amulet")
					]
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print([card.name for card in potentialValids])

			if "Location" in targetObj:
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print("This target is of location {0}.".format(targetObj["Location"]))
				if targetObj["Location"] == "onFriendlyBoard":
					potentialValids = [
						potential for potential in potentialValids 
						if potential.state == CARD_STATES.played 
						and potential.cardNum in owner.cardNumbers
					]
				if targetObj["Location"] == "onEnemyBoard":
					potentialValids = [
						potential for potential in potentialValids 
						if potential.state == CARD_STATES.played 
						and potential.cardNum in game.getOtherPlayer(owner).cardNumbers
					]
				if targetObj["Location"] == "inFriendlyHand":
					potentialValids = [
						potential for potential in potentialValids 
						if potential.state == CARD_STATES.held
						and potential.cardNum in owner.cardNumbers
					]
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print([card.name for card in potentialValids])

			if "Test" in targetObj:
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print("This target has a test: {0}.".format(targetObj["Test"]))
				failedTest = []
				for target in potentialValids:
					if eval(targetObj["Test"]) == False:
						failedTest.append(target)
				potentialValids = [
					target for target in potentialValids
					if target not in failedTest
				]
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print([card.name for card in potentialValids])

			for potential in potentialValids:
				if potential not in valids:
					valids.append(potential)

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.targets]: print("We've ended up with {0} valid targets.".format(len(valids)))
		return valids

	def registerCard(self, player, card):
		"""Gets a new unique index and passes it to the player, then returns the index.

		Args:
				player (Player): the player who owns this card
				card (Card): the card

		Returns:
				Integer: the unique index given to this card.
		"""
		player.addOwnedCard(self.cardNumCounter)
		self.cards.append(card)
		self.cardNumCounter += 1
		return self.cardNumCounter - 1

	def getCardsMatching(self, criteria):
		"""Get cards matching the criteria given.

		Args:
				criteria (List(Object)): A list of criteria objects containing fields such as "Type", "Location", and an eval string, "Test".

		Returns:
				List(Card): a list of cards matching the given criteria.
		"""
		# TODO
		return []

	def getEvolvableMonsters(self, player):
		"""Returns evolvable monsters the player has on board. Monsters can be Evolved from a pool of 2 points, 3 for the second player. Evolving flips their face, granting them extra abilities and improved stats--usually +2/+2. Players can evolve on their 4th turn, but only once per turn.

		Args:
				player (Player): the player we're checking

		Returns:
				List(MonsterCard): the evolvable monsters the player has.
		"""
		return [card for card in player.board.getCards() if card.isOfType(CARD_TYPES.monster) and not card.isEvolved]

class Gameplay:
	"""A Gameplay class holding the logic of the game, such as rounds and players.
	"""
	def __init__(self, players):
		"""Initializes the gameplay object with a given list of players.

		Args:
				players (List(Player)): a list of players involved in the game. Must be 2.
		"""
		if len(players) != 2:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.errors]: print("Improper number of players! Must be 2.")
			return
		self.players = players
		self.activePlayer = players[0]
		self.turnNum = 0
		self.isPlaying = False


	def getOtherPlayer(self, player):
		"""Get the opposing player to a given player.

		Args:
				player (Player): the player not being searched for

		Returns:
				Player: the opposing player.
		"""
		if player == self.players[0]:
			return self.players[1]
		return self.players[0]


	def startGame(self):
		"""Starts the game, beginning with a mulligan and then deciding the first player, whose turn starts.
		"""
		self.players[0].initialize()
		self.players[0].draw(3)
		self.players[1].initialize()
		self.players[1].draw(4)

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Game started.")
		# self.mulligan()
		# TODO

		self.isPlaying = True
		self.startTurn(self.players[self.coinToss()])

	def mulligan(self):
		"""Mulligans, allowing the first player to redraw up to three cards, then the second player.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Mulliganing:")
		player1 = self.players[0]
		player2 = self.players[1]

		player1.draw(3)
		print(str(player1.hand))

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playerInput]: print("Type 1-3 to redraw those cards.")
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playerInput]: print("When you're done, type q.")

		redrawing = [False, False, False]
		while(True): 
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Currently redrawing: {0}, {1}, {2}".format(
				redrawing[0], redrawing[1], redrawing[2])
			)
			typed = input("Select a card to redraw:")
			if typed == "q":
				break
			if typed == "1" or typed == "2" or typed == "3":
				redrawing[int(typed) - 1] = not redrawing[int(typed) - 1]

		for i in range(3):
			if redrawing[i]:
				card = player1.hand.cards[i]
				player1.hand.shuffleCard(card)
				player1.deck.addCard(card)
				player1.deck.shuffle()
				player1.draw()

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(str(player1.hand))

		player2.draw(3)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(str(player2.hand))

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playerInput]: print("Type 1-3 to redraw those cards.")
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.playerInput]: print("When you're done, type q.")

		redrawing = [False, False, False]
		while(True): 
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Currently redrawing: {0}, {1}, {2}".format(
				redrawing[0], redrawing[1], redrawing[2])
			)
			typed = input("Select a card to redraw:")
			if typed == "q":
				break
			if typed == "1" or typed == "2" or typed == "3":
				redrawing[int(typed) - 1] = not redrawing[int(typed) - 1]

		for i in range(3):
			if redrawing[i]:
				card = player2.hand.cards[i]
				player2.hand.shuffleCard(card)
				player2.deck.addCard(card)
				player2.deck.shuffle()
				player2.draw()

		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(str(player2.hand))

	def coinToss(self):
		"""Picks a random player.

		Returns:
				Player: the player chosen randomly.
		"""
		firstPlayer = 0
		if random.random() > 0.5:
			firstPlayer = 1
		firstPlayer = 0 # THIS IS TO ENFORCE P1 start
		return firstPlayer

	def startTurn(self, player):
		"""Starts a given player's turn. Increments the current turn number, and if it's the second player's first turn, they get an extra card.

		Args:
				player (Player): the player whose turn it is
		"""
		self.turnNum += 1
		self.activePlayer = player
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0}'s turn.".format(player.name))
		player.startTurn()

		if self.turnNum == 2:
			player.draw()

		while self.isPlaying:
			self.chooseActionLoop(player)

	def chooseActionLoop(self, player):
		"""Sticks the player in a looping choice of actions. Players can play cards, attack with them, or evolve MonsterCards.

		Args:
				player (Player): the player who's making choices.
		"""
		while self.isPlaying:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("--------------LOOP RESET---------------")
			enemy = game.getOtherPlayer(player)
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(enemy)
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(str(enemy.board))
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(str(player.board))
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(str(player.hand))
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print(player)

			handCards = player.hand.getCards()
			boardCards = player.board.getCards()

			out = "Type the number of the card you wish to use. {0} cards on board".format(len(boardCards))
			if len(boardCards) > 0:
				out += ", starting with 1"
			out += ". {0} cards in hand".format(len(handCards))
			if len(handCards) > 0:
				out += ", starting with {0}.".format(len(boardCards) + 1)
			if player.canEvolve() and len(logic.getEvolvableMonsters(player)) > 0:
				out += " Or type 'evo' to evolve a monster."
			out += " Or type 'end' to end your turn."
			choice = input(out)
			
			if choice == "end":
				break
			elif choice == "evo":
				if len(logic.getEvolvableMonsters(player)) == 0:
					break
				evolveTarget = self.chooseTargets(logic.getEvolvableMonsters(player))
				player.evolveMonster(evolveTarget[0])
			elif int(choice) <= len(boardCards):
				card = player.board.cards[int(choice) - 1]
				if logic.canAttackWithCard(player, card):
					target = self.chooseTargets(logic.getValidTargets(player, [{"Type": "EnemyPlayer"}, {"Type": "Monster", "Location": "onEnemyBoard"}]))
					if isinstance(target[0], Player):
						player.attackEnemy(card)
					else :
						player.attackCard(card, target[0])
				else :
					if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Can't attack with that card.")
			else :
				card = player.hand.cards[int(choice) - len(boardCards) - 1]
				if logic.canPlayCard(player, card):
					if player.energy < card.cost and card.accelerate:
						player.playAccelerate(card)
					else :
						player.playCard(card)
				else :
					if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Can't play that card.")
		if not self.isPlaying:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Game's over.")
			return
		player.endTurn()

	def chooseTargets(self, targets, numTargets=1):
		"""Choose a number of targets from a given list of available ones.

		Args:
				targets (List(Player or Card)): a list of targets available to choose from, Card or Player.
				numTargets (Integer, optional): number of targets to be chosen. Defaults to 1.

		Returns:
				List(Player or Card): a list of the targets chosen.
		"""
		targetChoices = []
		while len(targetChoices) < numTargets:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.playerInput]: print("Please choose a target. {0} targets remain.".format(numTargets - len(targetChoices)))
			options = [target for target in targets if target not in targetChoices]
			output = [str(option) for option in options]
			choice = input(" ".join(output))
			targetChosen = options[int(choice) - 1]
			targetChoices.append(targetChosen)
		return targetChoices

class Player:
	"""A player object containing fields like a name, a list of cards, and values like health and energy. Also contains a Deck, a Hand and a Board object.
	"""
	def __init__(self, name, cardList):
		"""Initializes the player object. Creates an empty effects object and an empty list of card indices.

		Args:
				name (String): the name of the player
				cardList (List(String)): a list of card names in the player's deck
		"""
		self.name = name
		self.cardList = cardList
		self.cardNumbers = []
		self.effects = [[] for i in TRIGGER_TYPES]

	def __str__(self):
		"""A Stringing method for the player.

		Returns:
				String: the player's name and attributes represented in words.
		"""
		return "{0}: {1} health, {2}/{3} energy, {4} shadows, {5} evolves, {6} cards in hand, {7} cards in deck.".format(self.name, self.health, self.energy, self.totalEnergy, self.shadows, self.evolutions, len(self.hand.getCards()), len(self.deck.getCards()))
		
	def initialize(self):
		"""Initializes the player at game start. Sets all values to their base amounts.
		"""
		self.maxHealth = 20
		self.health = 20
		self.deck = Deck(self.cardList, self)
		self.hand = Hand(self)
		self.board = Board(self)
		self.energy = 0
		self.totalEnergy = 0
		self.shadows = 0
		self.turnsPlayed = 0
		self.invocationsThisTurn = []
		self.evolutions = 3
		self.totalEvolutions = 3
		self.hasEvolvedThisTurn = False

		# self.totalEnergy = self.energy = 10
		# self.maxHealth = self.health = 1


	def canEvolve(self):
		"""Checks whether the player can evolve. Monsters can be Evolved from a pool of 2 points, 3 for the second player. Evolving flips their face, granting them extra abilities and improved stats--usually +2/+2. Players can evolve on their 4th turn, but only once per turn.

		Returns:
				bool: whether the player can evolve.
		"""
		return self.turnsPlayed >= 3 and not self.hasEvolvedThisTurn


	def registerEffect(self, trigger, effect):
		"""Adds a given effect to the player with a given trigger.

		Args:
				trigger (TriggerType): the trigger the effect fires on
				effect (Effect): the effect to be appended to the player
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Registering an effect on {0}:".format(self.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print(effect.effect)
		if effect.isUnstackable and self.effectRegistered(effect):
			return
		self.effects[trigger].append(effect)

	def effectRegistered(self, effect):
		"""Checks whether a given effect is already registered.

		Args:
				effect (Effect): the effect to be tested against

		Returns:
				Boolean: whether the effect is already registered on this player.
		"""
		for triggerType in self.effects:
			for registeredEffect in self.effects[triggerType]:
				if effect == registeredEffect:
					return True
		return False

	def resolveSelf(self, trigger, **kwargs):
		"""Resolves effects on this player registered on the given trigger.

		Args:
				trigger (TriggerType): the type of trigger resolving
				kwargs (kwargs): a list of keyword arguments necessary to pop the effects, such as number of shadows used in Necromancy
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Self resolving {0}.".format(trigger.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		for triggerEffects in self.effects:
			for effect in triggerEffects:
				effect.refill(trigger)
		for effect in self.effects[trigger]:
			effect.resolve(**kwargs)

	def resolveAllCards(self, trigger, **kwargs):
		"""Resolves effects on all cards in this player's hand, deck and field using a given trigger.

		Args:
				trigger (TriggerType): the type of trigger resolving
				kwargs (kwargs): a list of keyword arguments necessary to pop the effects, such as number of shadows used in Necromancy
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		for card in self.hand.getCards():
			card.refill(trigger)
			card.resolve(trigger, **kwargs)
		for card in self.board.getCards():
			card.refill(trigger)
			card.resolve(trigger, **kwargs)
		for card in self.deck.getCards():
			card.refill(trigger)
			card.resolve(trigger, **kwargs)

	def resolveAll(self, trigger, **kwargs):
		"""Resolves effects on all cards in this player's hand, deck and field, and themselves using a given trigger.

		Args:
				trigger (TriggerType): the type of trigger resolving
				kwargs (kwargs): a list of keyword arguments necessary to pop the effects, such as number of shadows used in Necromancy
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Resolving trigger {0}".format(trigger.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		self.resolveSelf(trigger, **kwargs)
		self.resolveAllCards(trigger, **kwargs)

	def resolve(self, cards, trigger, **kwargs):
		"""Resolves effects on all cards in the given list using a given trigger.

		Args:
				cards (List(Card)): the cards to be tested for effect resolution
				trigger (TriggerType): the type of trigger resolving
				kwargs (kwargs): a list of keyword arguments necessary to pop the effects, such as number of shadows used in Necromancy
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		for card in cards:
			card.refill(trigger)
			card.resolve(trigger, **kwargs)


	def startTurn(self):
		"""Starts this player's turn and prints out their side of the field.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("----------------------------NEW TURN---------------------------------")
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0}'s turn has started.".format(self.name))
		self.draw()
		self.gainTotalEnergy()
		self.refillEnergy()
		for card in self.board.cards:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.interactions]: print(card)
			if isinstance(card, MonsterCard):
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.interactions]: print(card)
				card.attackState = ATTACK_STATES.storm
		self.resolveAll(TRIGGER_TYPES.onFriendlyTurnStart)
		game.chooseActionLoop(self)

	def attackEnemy(self, card):
		"""This player attacks the opposing player with a given card.

		Args:
				card (MonsterCard): the attacking card.
		"""
		card.resolve(TRIGGER_TYPES.onAttacking)
		card.resolve(TRIGGER_TYPES.onLeaderClashing)
		enemy = game.getOtherPlayer(self)
		enemy.takeDamage(card.attack)
		card.resolve(TRIGGER_TYPES.onDealtDamage)
		if "Drain" in card.effects:
			self.gainHealth(card.attack)
		card.attackState = ATTACK_STATES.attacked
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} attacks {1} for {2} damage. {3} health remains.".format(card.name, enemy.name, card.attack, enemy.health))

	def attackCard(self, card, target):
		"""This player attacks the given target card with the given card.

		Args:
				card (MonsterCard): the attacking card
				target (MonsterCard): the card being attacked
		"""
		card.resolve(TRIGGER_TYPES.onAttacking)
		card.resolve(TRIGGER_TYPES.onClashing)
		target.resolve(TRIGGER_TYPES.onClashing)
		target.takeDamage(card.attack)
		card.resolve(TRIGGER_TYPES.onDealtDamage)
		if "Drain" in card.effects:
			self.gainHealth(card.attack)
		target.resolve(TRIGGER_TYPES.onTookDamage)
		if "Bane" in card.effects:
			target.destroy()
		card.takeDamage(target.attack)
		target.resolve(TRIGGER_TYPES.onDealtDamage)
		card.resolve(TRIGGER_TYPES.onTookDamage)
		if "Bane" in target.effects:
			card.destroy()
		card.attackState = ATTACK_STATES.sickness

	def endTurn(self):
		"""Ends this player's turn.
		"""
		for card in self.board.getCards():
			card.triggerPop(TRIGGER_TYPES.onFriendlyTurnEnd)
		for card in self.hand.getCards():
			card.triggerPop(TRIGGER_TYPES.onFriendlyTurnEnd)
		self.invocationsThisTurn = []
		self.turnsPlayed += 1
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0}'s turn has ended.".format(self.name))
		game.getOtherPlayer(self).startTurn()

	def die(self):
		"""This player loses the game.
		"""
		print(self.name + " has lost!")
		game.isPlaying = False
	

	def registerCard(self, num):
		"""Registers a card's unique index with this player.

		Args:
				num (Integer): the unique index of the card
		"""
		self.cardNumbers.append(num)

	def drawCard(self, card):
		"""This player draws a given card from their Deck.

		Args:
				card (Card): the card to be drawn
		"""
		self.deck.removeCard(card)
		self.hand.addCard(card)

	def draw(self, numCards=1):
		"""This player draws a given number of cards. Usually 1.

		Args:
				numCards (Integer, optional): the number of cards to draw. Defaults to 1.
		"""
		for i in range(numCards):
			card = self.deck.draw()
			if (len(self.deck.cards) <= 0):
				self.die()
			self.hand.addCard(card)

	def addCards(self, cardNames):
		"""This player adds cards to their hand without taking them from their deck. In some circumstances, the cards may not even be in their deck.

		Args:
				cardNames (List(String)): a list of card names to be created and added to the hand
		"""
		for name in cardNames:
			card = cardbuilder.buildCard(name, self, CARD_STATES.held)
			card.registerAllEffects()
			self.hand.addCard(card)

	def playCard(self, card, costless=False):
		"""This player plays a given card.

		Args:
				card (Card): the card to be played
				costless (Boolean, optional): whether the card doesn't require energy to play. Defaults to False.
		"""
		if not costless: 
			self.spendEnergy(card.cost)
		if card in self.hand.getCards(): 
			self.hand.removeCard(card)
		if card.isOfType("Amulet") or card.isOfType("Monster"):
			self.board.playCard(card)
		card.onPlay()
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} played {1}.".format(self.name, card.name))

	def playFromDeck(self, card):
		"""This player plays a given card straight from their deck. This is always costless.

		Args:
				card (Card): the card to be played
		"""
		self.deck.removeCard(card)
		card.registerAllEffects()
		if card.isOfType("Amulet") or card.isOfType("Monster"):
			self.board.playCard(card)
		card.onPlay()
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} played {1} from deck.".format(self.name, card.name))

	def playAccelerate(self, card, costless=False):
		"""This player plays a given card's Accelerate ability, playing a MonsterCard as a SpellCard. Some Monsters have Accelerate abilities allowing them to be played as Spells at reduced cost.

		Args:
				card (Card): the card to be accelerated
				costless (Boolean, optional): whether the card doesn't require energy to play. Defaults to False.
		"""
		if not costless:
			self.spendEnergy(card.accelerate["Cost"])
		self.hand.discard(card)
		card.onAccelerate()
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} played {1} accelerated.".format(self.name, card.name))

	def playCardNames(self, cards):
		"""This player plays a given list of cards, constructing them from their names.

		Args:
				cards (List(String)): list of card names
		"""
		for card in cards:
			builtCard = cardbuilder.buildCard(card, self, CARD_STATES.played)
			builtCard.registerAllEffects()
			self.board.playCard(builtCard)


	def burialRite(self, card):
		"""Burial Rites the given card, stripping its effects and playing it, then destroying it. Some cards allow for Burial Rites, which discards a card but lets it effectlessly hit the board first.

		Args:
				card (Card): the card to be Burial Rited
		"""
		if not self.board.hasSpace(): 
			return
		card.effects = [[] for i in TRIGGER_TYPES]
		card.abilities = []
		self.playCard(card, True)
		card.destroy()

	def tutor(self, **kwargs):
		"""This player takes a card from their deck matching the keyword arguments given.

		Args:
				kwargs (keywords): the criteria from which the available cards are picked.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Tutoring:")
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print(kwargs)
		potentials = []
		for card in self.deck.getCards():
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print(card.name)
			if "type" in kwargs and not card.isOfType(kwargs["type"]):
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Type {0} doesn't fit our type, {1}.".format(card.cardObj["Type"], kwargs["type"]))
				continue
			if "craft" in kwargs and card.cardObj["Craft"] != kwargs["craft"]:
				if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Craft {0} doesn't fit our craft, {1}.".format(card.cardObj["Craft"], kwargs["craft"]))
				continue
			potentials.append(card)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print(", ".join([card.name]))

		if len(potentials) == 0:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("No cards meeting our criteria.")
			return
		random.shuffle(potentials)
		self.drawCard(potentials[0])

	def necromancy(self, necroCost, shadows):
		"""This player performs Necromancy at the given cost, spending the given number of shadows. Necromancy resurrects a random destroyed MonsterCard with base cost equal to the given cost. If no destroyed MonsterCards are available at that cost, a MonsterCard of close lower value is resurrected instead.

		Args:
				shadows ([type]): [description]
		"""
		self.shadows -= shadows
		# TODO
		self.resolveAll(TRIGGER_TYPES.onFriendlyNecromancy, shadows=shadows)

	def invokeCard(self, card):
		"""Invokes a given card, playing it straight from the deck. Some cards have Invocation, which means when specific requirements are met, they are played from the player's deck.

		Args:
				card (Card): the card to be invoked
		"""
		if self.board.hasSpace() and card.name not in self.invocationsThisTurn and card in self.deck.getCards():
			self.playFromDeck(card)
			self.invocationsThisTurn.append(card.name)


	def evolveMonster(self, card):
		"""Evolves a card. Monsters can be Evolved from a pool of 2 points, 3 for the second player. Evolving flips their face, granting them extra abilities and improved stats--usually +2/+2. Players can evolve on their 4th turn, but only once per turn.

		Args:
				card (MonsterCard): the card to be evolved
		"""
		card.onEvolve()
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} evolves {1}!".format(self.name, card.name))


	def takeDamage(self, amount):
		"""This player takes a given amount of damage. If they end up below or at 0, they lose.

		Args:
				amount (Integer): the amount of health lost
		"""
		self.health -= amount
		if self.health <= 0:
			self.die()

	def gainHealth(self, amount):
		"""This player gains a given amount of health. Usually the cap is 20, and the excess is lost.

		Args:
				amount (Integer): the amount of health gained
		"""
		self.health += amount
		if self.health > self.maxHealth:
			self.health = self.maxHealth

	def refillEnergy(self):
		"""This player refills their energy to their current max.
		"""
		self.energy = self.totalEnergy

	def gainTotalEnergy(self, amount=1):
		"""This player increases their total energy by the given amount, usually 1. The cap is 10.

		Args:
				amount (Integer, optional): the amount of energy the cap is increased by. Defaults to 1.
		"""
		self.totalEnergy += amount
		if self.totalEnergy > 10:
			self.totalEnergy = 10
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.resources]: print("Gaining {0} total energy. New amount: {1}.".format(amount, self.totalEnergy))

	def gainEnergy(self, amount=1):
		"""This player increases their current energy by the given amount, usually 1. The cap is their total energy amount.

		Args:
				amount (Integer, optional): the amount of energy their current energy is increased by. Defaults to 1.
		"""
		self.energy += amount
		if self.energy > self.totalEnergy:
			self.energy = self.totalEnergy
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.resources]: print("Gaining {0} energy. New amount: {1}.".format(amount, self.energy))

	def spendEnergy(self, amount):
		"""This player spends a given amount of energy.

		Args:
				amount (Integer): the amount of energy spent
		"""
		self.energy -= amount

	def gainShadows(self, amount=1):
		"""This player gains a given number of Shadows. Usually 1. Shadows are a resource loosely tied to graveyard count. Discarded and destroyed cards add 1 to the owner's Shadows.

		Args:
				amount (Integer, optional): the amount of shadows to add. Defaults to 1.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.resources]: print("Gained {0} shadows.".format(amount))
		self.shadows += amount

class Deck:
	"""A Deck object storing a list of cards, belonging to a player.
	"""

	def __init__(self, cards, owner):
		"""The initializing method. Creates an empty card list and populates it, building Card objects from a list of card name strings.

		Args:
				cards (List(String)): a list of card names in the deck
				owner (Player): the owner of this deck
		"""
		self.owner = owner
		self.cards = []
		print(cards)
		for card in cards:
			self.cards.append(cardbuilder.buildCard(card, owner, CARD_STATES.inDeck))
		print("Finished populating deck.")
		random.shuffle(self.cards)


	def shuffle(self):
		"""Shuffles this deck.
		"""
		random.shuffle(self.cards)

	def draw(self):
		"""Takes the top card from the card list.

		Returns:
				Card: the top card
		"""
		return self.cards.pop()

	def getCards(self):
		"""Gets the list of cards in the deck.

		Returns:
				List(Card): a list of cards in the deck
		"""
		return self.cards

	def addCard(self, card):
		"""Adds a card to the bottom of the deck.

		Args:
				card (Card): the card to be inserted
		"""
		self.cards.insert(0, card)

	def removeCard(self, card):
		"""Removes the given card from the deck list.

		Args:
				card (Card): the card to be removed
		"""
		self.cards.remove(card)

	def removeCardAt(self, index):
		"""Removes the card from the deck list at the given index.

		Args:
				index (Integer): index location of the card ot be removed
		"""
		del self.cards[index]

class Hand:
	"""A Hand object holding a list of cards in a given player's hand.
	"""

	def __init__(self, owner):
		"""Initializing method. Creates an empty list of cards and sets the owner.

		Args:
				owner (Player): the owner of this hand
		"""
		self.cards = []
		self.owner = owner

	def __str__(self):
		"""A stringing method to output the hand to the console.

		Returns:
				String: a string of cards in the hand
		"""
		return "Hand: " + " | ".join([str(card) for card in self.cards])


	def addCard(self, card):
		"""Try to add a card to this hand. If it puts us over the 9-card hand limit, we discard it instead.

		Args:
				card (Card): the card being added
		"""
		if len(self.cards) > 9:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} discarded.".format(card.name))
			self.owner.gainShadows()
		else :
			self.cards.append(card)
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("Drew {0}.".format(card.name))
			card.onDraw()

	def removeCard(self, card):
		"""Remove the given card from the hand without discarding it.

		Args:
				card (Card): the card to be removed
		"""
		self.cards.remove(card)

	def discard(self, card):
		"""Discards a given card from the hand, gaining a shadow in the process.

		Args:
				card (Card): the card to be discarded
		"""
		if card in self.cards:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} discarded.".format(card.name))
			self.cards.remove(card)
			self.owner.gainShadows()
		else :
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.errors]: print("{0} isn't in the hand!".format(card.name))

	def getCards(self):
		"""Getter function for the list of cards held in the hand.

		Returns:
				List(Card): the list of cards in the hand
		"""
		return self.cards

class Board:
	"""A Board object holding a list of cards played by the owner.
	"""

	def __init__(self, owner):
		"""Initializes the object, creating an empty list of cards for the given owner.

		Args:
				owner (Player): the owner of the board
		"""
		self.cards = []
		self.owner = owner

	def __str__(self):
		"""A stringing method for the board and the cards on it.

		Returns:
				String: a string of the cards on the board.
		"""
		return "Board: " + " | ".join([str(card) for card in self.cards])


	def playCard(self, card):
		"""Plays a given card onto this board.

		Args:
				card (Card): the card to be played
		"""
		if len(self.cards) == 5:
			if ACTIVE_DEBUG_STATES[DEBUG_STATES.errors]: print("{0} can't be played. Too many cards on the field!".format(card.name))
			return
		self.cards.append(card)

	def getCards(self):
		"""Getter function for the list of cards on the board.

		Returns:
				List(Cards): the list of cards on the board
		"""
		return self.cards

	def removeCard(self, card):
		"""Removes a given card on the board.

		Args:
				card (Card): the card to be removed
		"""
		self.cards.remove(card)

	def hasSpace(self):
		"""Checks whether there's space for another card to be on the board. Cap is 5.

		Returns:
				Boolean: whether there's space left on the board or not
		"""
		return len(self.cards) < 5

# CARD CONSTRUCTOR
class CardBuilder:
	"""CardBuilder class to build a Card object from a card name, pulling from a JSON library.
	"""

	def __init__(self):
		pass

	def buildCard(self, cardName, owner, state):
		"""Builds a card object given its name, its owner, and the current state it's in.

		Args:
				cardName (String): the name of the card
				owner (Player): the owner of the card
				state (CARD_STATES): the current state of the card

		Returns:
				Card: the Card object--MonsterCard, AmuletCard or SpellCard
		"""
		cardObj = library[cardName]
		card = None
		if cardObj["Type"] == "Monster":
			card = MonsterCard(owner, state, cardObj)
		elif cardObj["Type"] == "Spell":
			card = SpellCard(owner, state, cardObj)
		elif cardObj["Type"] == "Amulet":
			card = AmuletCard(owner, state, cardObj)

		card.registerGameStartEffects()

		return card

# CARD LITERALS
class Card:
	"""Card object base for several extensions: Monster, Spell and Amulet
	"""

	def __init__(self, name, cost, base, owner, state, cardObj):
		"""Initializes the Card object, setting its basic values. Registers and generates a unique index for the card.

		Args:
				name (String): the name of the card
				cost (Int): the cost of the card
				base (CardFace): the effect, ability and resource holder for this card
				owner (Player): the owner of the card
				state (CARD_STATES): the state of the card
				cardObj (Object): the unedited object of this card
		"""
		self.name = name
		self.cost = cost
		self.baseFace = base
		self.activeFace = self.baseFace
		self.effects = [[] for i in TRIGGER_TYPES]
		self.owner = owner
		self.state = state
		self.cardObj = cardObj
		self.cardNum = logic.registerCard(owner, self)
		self.trait = cardObj.setdefault("Trait", None)
		self.type = None

	def __eq__(self, other):
		"""An comparative function to compare Cards. Compares only the objects they are and the unique card numbers they hold.

		Args:
				other (Card): the opposing card being compared

		Returns:
				bool: whether the two cards are equal
		"""
		if not isinstance(other, Card):
			return False
		return self.cardNum == other.cardNum


	def getActiveEffects(self):
		"""Gets a list of active effects on the card.

		Returns:
				List(List(Effect)): a list of list of effects, indexed by TRIGGER_TYPES.
		"""
		combinedEffects = [[] for i in TRIGGER_TYPES]
		for i in range(len(TRIGGER_TYPES)):
			combinedEffects[i] = self.effects[i] + self.activeFace.effects[i]
		return combinedEffects

	def isOfType(self, typename):
		"""Checks whether this card is of a specific type: Monster, Spell or Amulet

		Args:
				typename (String or CARD_TYPES): a string like "Monster" or a CARD_TYPES enum like .amulet
		"""
		if not self.type:
			return False
		elif self.type is CARD_TYPES.monster:
			return typename is self.type or typename is "Monster"
		elif self.type is CARD_TYPES.spell:
			return typename is self.type or typename is "Spell"
		elif self.type is CARD_TYPES.amulet:
			return typename is self.type or typename is "Amulet"


	def registerGameStartEffects(self):
		"""Registers effects on this card before it's drawn--only Invocation.
		"""
		self.baseFace.registerGameStartEffects()

	def registerAllEffects(self):
		"""Registers all effects on this card.
		"""
		self.baseFace.registerAllEffects()

	def registerEffect(self, triggerType, effect):
		"""Registers a given effect on this card, with a given trigger.

		Args:
				triggerType (TRIGGER_TYPES): the type of trigger which provokes this effect
				effect (Effect): the effect triggered
		"""
		self.effects[triggerType].append(effect)

	def triggerPop(self, triggerType, **kwargs):
		"""Refills and then triggers all effects on this card which match the given trigger.

		Args:
				triggerType (TRIGGER_TYPES): the trigger popped
				**kwargs (Keyword arguments): a list of keyword arguments carrying information for the effects, such as Shadows used in a Necromancy effect.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("{0} popped.".format(triggerType.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		self.activeFace.refillEffects(triggerType)
		self.refillEffects(triggerType)
		self.activeFace.resolveEffects(triggerType)
		self.resolveEffects(triggerType, **kwargs)

	def resolveEffects(self, triggerType, **kwargs):
		"""Activates all triggers on this card which match the given trigger.

		Args:
				triggerType (TRIGGER_TYPES): the trigger popped
				**kwargs (Keyword arguments): a list of keyword arguments carrying information for the effects, such as Shadows used in a Necromancy effect.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Resolving " + triggerType.name)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		for effect in self.effects[triggerType]:
			effect.resolve(**kwargs)

	def refillEffects(self, triggerType):
		"""Refills all effects in this card which match the given trigger. Some Effects have a number of times they can go off, but can be refilled for more activations.

		Args:
				triggerType (TRIGGER_TYPES): the trigger popped
		"""
		for triggerEffects in self.effects:
			for effect in triggerEffects:
				effect.refill(triggerType)


	def onDraw(self):
		"""Method called when card is drawn, changing its state and registering all its effects.
		"""
		self.state = CARD_STATES.held
		self.registerAllEffects()

class SpellCard(Card):
	"""A SpellCard object extending the Card framework. For cards which are played once, then destroyed.

	Args:
			Card (Card): base object extended
	"""

	def __init__(self, owner, state, cardObj):
		"""Initializes the card, setting its base values.

		Args:
				owner (Player): the owner of this card
				state (CARD_STATES): the current state of this card
				cardObj (Object): the unmodified object of this card
		"""
		base = CardFace(self, cardObj["base"])
		Card.__init__(self, cardObj["Name"], cardObj["Cost"], base, owner, state, cardObj)
		self.targets = cardObj["Base"].setdefault("Targets", None)
		self.type = CARD_TYPES.spell

	def __str__(self):
		"""Stringing method for SpellCards.

		Returns:
				String: a console-ready output depicting this card
		"""
		if logic.canPlayCard(self.owner, self):
			return "({0}: {1}.) ".format(self.cost, self.name)
		return "{0}: {1}.".format(self.cost, self.name)


	def onPlay(self):
		"""Triggered on play. Gathers targets if applicable, then runs its effects.
		"""
		if self.targets:
			targets = game.chooseTargets(logic.getValidTargets(self.owner, self.targets))
			self.triggerPop(TRIGGER_TYPES.onPlayed)
			self.triggerPop(TRIGGER_TYPES.onTargetsChosen, targets=targets)
			self.state = CARD_STATES.destroyed
		else :
			self.state = CARD_STATES.played
			self.triggerPop(TRIGGER_TYPES.onPlayed)
		self.onDestroy()

	def onDestroy(self):
		"""Triggered when this card is destroyed. Gains the owner a shadow.
		"""
		self.owner.gainShadows()

	def onFriendlyTurnStart(self):
		"""Triggered when the owner's turn starts.
		"""
		# self.triggerPop(TRIGGER_TYPES.onFriendlyTurnStart)

class MonsterCard(Card):
	"""A SpellCard object extending the Card framework. For cards which are played onto the battlefield with an attack and a defense value.

	Args:
			Card (Card): base object extended
	"""

	def __init__(self, owner, state, cardObj):
		"""Initializes the card, setting its base values.

		Args:
				base (MonsterFace): the basic face on this card, storing effects and abilities
				evolve (MonsterFace): the evolved face on this card, storing effects and abilities
				owner (Player): the owner of this card
				state (CARD_STATES): the current state of this card
				cardObj (Object): the unmodified object of this card
		"""

		base = MonsterCard(cardObj["Base"]["Attack"], cardObj["Base"]["Defense"], cardObj["Base"])
		self.evolveFace = None
		if "Evolve" in cardObj:
			self.evolveFace = MonsterCard(cardObj["Evolve"].setdefault("AttackChange", 2), cardObj["Evolve"].setdefault("DefenseChange", 2), cardObj["Evolve"])
		else :
			self.evolveFace = MonsterCard(2, 2, {})
		Card.__init__(self, cardObj["Name"], cardObj["Cost"], base, owner, state, cardObj)
		self.state = state
		self.attack = self.baseFace.attack
		self.defense = self.baseFace.defense
		self.attackState = None
		self.abilities = cardObj.setdefault("Abilities", [])
		self.accelerate = cardObj.setdefault("Accelerate", None)
		self.enhance = cardObj.setdefault("Enhance", None)
		self.type = CARD_TYPES.monster
		self.isEvolved = False

	def __str__(self):
		"""Stringing method for MonsterCards.

		Returns:
				String: a console-ready output depicting this card
		"""
		if self.state == CARD_STATES.held:
			if self.accelerate and self.owner.energy < self.cost:
				if logic.canPlayCard(self.owner, self):
					return "({0}: {1}. {2}/{3}.)".format(self.accelerate["Cost"], self.name, self.attack, self.defense)
				return "{0}: {1}. {2}/{3}.".format(self.accelerate["Cost"], self.name, self.attack, self.defense)
			else :
				if logic.canPlayCard(self.owner, self):
					return "({0}: {1}. {2}/{3}.)".format(self.cost, self.name, self.attack, self.defense)
				return "{0}: {1}. {2}/{3}.".format(self.cost, self.name, self.attack, self.defense)
		else :
			if logic.canAttackWithCard(self.owner, self):
				return "({0}: {1}. {2}/{3}. {4}.)".format(self.cost, self.name, self.attack, self.defense, self.attackState)
			return "{0}: {1}. {2}/{3}. {4}.".format(self.cost, self.name, self.attack, self.defense, self.attackState)


	def getActiveAbilities(self):
		"""Gets a list of active abilities on the card.

		Returns:
				List(List(Effect)): a list of list of effects, indexed by TRIGGER_TYPES.
		"""
		return self.abilities + self.activeFace.abilities


	def registerAllEffects(self):
		"""Registers all effects on this card. This overloads the base method, since we have an evolve face too!
		"""
		self.baseFace.registerAllEffects()
		self.evolveFace.registerAllEffects()

	def removeEffects(self):
		"""Removes all effects and abilities on the monster.
		"""
		self.effects = [[] for i in TRIGGER_TYPES]
		self.abilities = []


	def buff(self, buff):
		"""Improves this card's stats by a given amount.

		Args:
				buff (List(2 integers)): the increases made to the current attack and defense.
		"""
		self.attack += buff[0]
		self.defense += buff[1]

	def takeDamage(self, amount):
		"""This monster takes a certain amount of damage. If its health falls to 0 or below, it dies.

		Args:
				amount (Integer): the amount of damage
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} damage dealt to {1}. New health: {2}.".format(amount, self.name, self.defense - amount))
		self.defense -= amount
		if self.defense <= 0:
			self.destroy()

	def destroy(self):
		"""This monster dies.
		"""
		self.triggerPop(TRIGGER_TYPES.onDestroying)
		owner = logic.getOwner(self.cardNum)
		owner.board.removeCard(self)
		owner.gainShadows()
		self.triggerPop(TRIGGER_TYPES.onDestroyed)
		self.triggerPop(TRIGGER_TYPES.onLeavesBoard)
		self.owner.resolveAll(TRIGGER_TYPES.onFriendlyCardDestroyed)
		game.getOtherPlayer(self.owner).resolveAll(TRIGGER_TYPES.onEnemyCardDestroyed)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} has been destroyed!".format(self.name))

	def banish(self):
		"""This monster's banished. It doesn't increase the owner's shadows and doesn't trigger on death effects.
		"""
		self.triggerPop(TRIGGER_TYPES.onBanishing)
		owner = logic.getOwner(self.cardNum)
		owner.board.removeCard(self)
		self.triggerPop(TRIGGER_TYPES.onBanished)
		self.triggerPop(TRIGGER_TYPES.onLeavesBoard)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} has been banished!".format(self.name))


	def onFriendlyTurnStart(self):
		"""Triggered on the owner's turn starting.
		"""
		self.triggerPop(TRIGGER_TYPES.onFriendlyTurnStart)
		self.attackState = ATTACK_STATES.storm

	def onPlay(self):
		"""Triggered on play. Manages card states.
		"""
		self.state = CARD_STATES.played
		self.attack = self.baseFace.attack
		self.defense = self.baseFace.defense
		self.attackState = ATTACK_STATES.sickness
		self.triggerPop(TRIGGER_TYPES.onPlayed)
		self.triggerPop(TRIGGER_TYPES.onEntersBoard)

	def onPlayEnhance(self):
		"""Triggered when this card is played, Enhanced. Some cards have an Enhance ability which costs more but improves their stats and abilities.
		"""
		self.attack = self.enhance.attack
		self.defense = self.enhance.defense

	def onAccelerate(self):
		"""Triggered when this card is played, Accelerated. Some cards have an Accelerate ability which costs less and makes the Monster be played like a Spell.
		"""
		for effect in self.accelerate["Effects"]:
			self.registerEffect(TRIGGER_TYPES[effect["Trigger"]], Effect(self, self.owner, effect))
		if "Targets" in self.accelerate:
			targets = game.chooseTargets(logic.getValidTargets(self.owner, self.accelerate["Targets"]))
			self.triggerPop(TRIGGER_TYPES.onPlayed)
			self.triggerPop(TRIGGER_TYPES.onTargetsChosen, targets=targets)
			self.triggerPop(TRIGGER_TYPES.onAccelerated)
			self.state = CARD_STATES.destroyed
		else :
			self.state = CARD_STATES.played
			self.triggerPop(TRIGGER_TYPES.onAccelerated)
			self.triggerPop(TRIGGER_TYPES.onPlayed)

	def onEvolve(self):
		"""Triggered on evolve. Switches face and activates its Evolve abilities. Monsters can be Evolved from a player's resource pool, usually giving them +2/+2, Rush, and special abilities.
		"""
		self.activeFace = self.evolveFace
		self.buff([self.attack.attack, self.attack.defense])
		self.isEvolved = True

class AmuletCard(Card):
	"""An AmuletCard object extending the Card framework. For cards which have no attack or defense, and sometimes a set lifetime. Some Amulets have a Countdown, which reduces by 1 at the beginning of its owner's turn and sometimes at other times as well. At 0 Countdown the Amulet is destroyed. 

	Args:
			Card (Card): base object extended
	"""

	def __init__(self, owner, state, cardObj):
		"""Initializes the card, setting its base values.

		Args:
				base (Object): the basic keywords and effects on this card
				owner (Player): the owner of this card
				state (CARD_STATES): the current state of this card
				cardObj (Object): the unmodified object of this card
		"""
		base = CardFace(self, cardObj["base"])
		Card.__init__(self, cardObj["Name"], cardObj["Cost"], base, owner, state, cardObj)
		self.countdown = cardObj["Base"].setdefault("Countdown", None)
		self.state = state
		self.type = CARD_TYPES.amulet

	def __str__(self):
		"""Stringing method for MonsterCards.

		Returns:
				String: a console-ready output depicting this card
		"""
		if self.state != CARD_STATES.played and logic.canPlayCard(self.owner, self):
			if self.countdown == None:
				return "({0}: {1}).".format(self.cost, self.name)
			return "({0}: {1}). Countdown {2}.".format(self.cost, self.name, self.countdown)
		else :
			if self.countdown == None:
				return "{0}: {1}.".format(self.cost, self.name)
			return "{0}: {1}. Countdown {2}.".format(self.cost, self.name, self.countdown)


	def destroy(self):
		"""This card is destroyed.
		"""
		self.triggerPop(TRIGGER_TYPES.onDestroying)
		owner = self.owner
		owner.board.removeCard(self)
		owner.gainShadows()
		self.triggerPop(TRIGGER_TYPES.onDestroyed)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} has been destroyed!".format(self.name))

	def banish(self):
		"""This card is banished, not adding to the owner's shadows nor triggering destroy effects.
		"""
		self.triggerPop(TRIGGER_TYPES.onBanishing)
		owner = self.owner
		owner.board.destroyCard(self)
		self.triggerPop(TRIGGER_TYPES.onBanished)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.basics]: print("{0} has been banished!".format(self.name))

	def reduceCountdown(self, amount=1):
		"""Reduces the countdown on the card. If it lowers below 1, the card destroys itself.

		Args:
				amount (Integer, optional): the amount to reduce the countdown by. Defaults to 1.
		"""
		if self.countdown == None:
			return
		self.countdown -= amount
		if self.countdown <= 0:
			self.destroy()


	def onFriendlyTurnStart(self):
		"""Triggered on the start of the owner's turn.
		"""
		self.reduceCountdown()
		self.triggerPop(TRIGGER_TYPES.onFriendlyTurnStart)

	def onPlay(self):
		"""Triggered on play. Manages card states.
		"""
		self.state = CARD_STATES.played
		self.triggerPop(TRIGGER_TYPES.onPlayed)

class CardFace:
	"""Card faces store effects, allowing us to play nice with effects on cards. Though we only really need it for MonsterCards, it's implemented universally for ease of use.
	"""

	def __init__(self, card, jsonObject):
		"""Initializing function.

		Args:
				card (Card): this face's card
				jsonObject (Object): the base object storing all the JSON info for this face
		"""
		self.card = card
		self.jsonObject = jsonObject
		self.effects = [[] for i in TRIGGER_TYPES]
		self.effectList = jsonObject.setDefault("Effects", [])


	def registerGameStartEffects(self):
		"""Registers effects on this face before it's drawn--only Invocation.
		"""
		if len(self.effectList) > 0:
			for effect in self.effectList:
				if "Type" in effect and effect["Type"] is "Invocation":
					self.registerEffect(TRIGGER_TYPES[effect["Trigger"]], Effect(self.card, self.card.owner, effect))

	def registerAllEffects(self):
		"""Registers all effects on this face.
		"""
		if len(self.effectList) > 0:
			for effect in self.effectList:
				if "Type" in effect and "Type" is "Invocation":
					break
				else :
					self.registerEffect(TRIGGER_TYPES[effect["Trigger"]], Effect(self.card, self.card.owner, effect))

	def registerEffect(self, triggerType, effect):
		"""Registers a given effect on this face, with a given trigger.

		Args:
				triggerType (TRIGGER_TYPES): the type of trigger which provokes this effect
				effect (Effect): the effect triggered
		"""
		self.effects[triggerType].append(effect)

	def triggerPop(self, triggerType, **kwargs):
		"""Refills and then triggers all effects on this face which match the given trigger.

		Args:
				triggerType (TRIGGER_TYPES): the trigger popped
				**kwargs (Keyword arguments): a list of keyword arguments carrying information for the effects, such as Shadows used in a Necromancy effect.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("{0} popped.".format(triggerType.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		self.refillEffects(triggerType)
		self.resolveEffects(triggerType, **kwargs)

	def refillEffects(self, trigger):
		"""Refills all effects in this card which match the given trigger. Some Effects have a number of times they can go off, but can be refilled for more activations.

		Args:
				trigger (TRIGGER_TYPES): the trigger popped
		"""
		for effects in self.effects:
			for effect in effects:
				effect.refill(trigger)
	
	def resolveEffects(self, trigger, **kwargs):
		"""Activates all triggers on this face which match the given trigger.

		Args:
				trigger (TRIGGER_TYPES): the trigger popped
				**kwargs (Keyword arguments): a list of keyword arguments carrying information for the effects, such as Shadows used in a Necromancy effect.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Resolving " + trigger.name)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		for effect in self.effects[trigger]:
			effect.resolve(**kwargs)

class MonsterFace(CardFace):
	"""Monster extension to Face object.

	Args:
			CardFace (Card): base card extended
	"""

	def __init__(self, attack, defense, card, jsonObject):
		"""Initializing function, setting values to their bases.

		Args:
				attack (Integer): attack stat
				defense (Integer): defense stat
				card (Card): this face's card
				jsonObject (Object): the base object storing all the JSON info for this face
		"""
		CardFace.__init__(self, card, jsonObject)
		self.attack = attack
		self.defense = defense
		self.jsonObject = jsonObject
		self.abilities = jsonObject.setdefault("Abilities", [])

# EFFECT SYSTEM
class Effect:
	"""Effect object, game effects triggered by events.
	"""

	def __init__(self, card, owner, effectObj):
		"""Initializing function. Sets values to their bases.

		Args:
				card (Card): the card this effect is registered from
				owner (Player): the owner of this effect
				effectObj (Object): the unmodified object of this effect
		"""
		self.card = card
		self.owner = owner
		self.effectObj = effectObj

		self.trigger = effectObj["Trigger"]
		self.effect = effectObj["Effect"]
		self.test = effectObj.setdefault("Test", None)
		self.maxAmount = effectObj.setdefault("Amount", -1)
		self.amount = effectObj.setdefault("Amount", -1)
		self.refillTrigger = effectObj.setdefault("Refill", None)
		self.isUnstackable = effectObj.setdefault("Unstackable", False)

	def __eq__(self, other):
		"""Comparitive method. Tests whether a given Effect is equal to this one. Loops over keys.

		Args:
				other (Effect): the comparing Effect object

		Returns:
				bool: whether the given effect is equal to this one.
		"""
		if not isinstance(other, Effect):
			return False
		if self.card.name != other.card.name:
			return False
		for key in self.effectObj:
			if key not in other.effectObj:
				return False
			if self.effectObj[key] != other.effectObj[key]:
				return False
		for key in other.effectObj:
			if key not in self.effectObj:
				return False
		return True


	def resolve(self, **kwargs):
		"""Triggers the effect, supplying optional kwargs.

		Args:
				**kwargs (Keyword arguments): arguments passing necessary values to the effect, such as number of shadows used in a Necromancy effect.
		"""
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Resolving {0}'s effect:".format(self.card.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print(self.effect)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.kwargs]: print(kwargs)
		if self.amount == 0:
			return
		if self.test and eval(self.test) == False:
			return

		if type(self.effect) is str:
			exec(self.effect)
		else :
			self.owner.registerEffect(TRIGGER_TYPES[self.effect["Trigger"]], Effect(self.card, self.owner, self.effect))

		self.amount -= 1
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("The new amount of this effect on {0} is {1}.".format(self.card.name, self.amount))

	def refill(self, trigger):
		"""Refills this effect. Some Effects can only be triggered a number of times, but can be refilled by certain events.

		Args:
				trigger (TRIGGER_TYPES): the trigger we're attempting to use to refill this effect.
		"""
		if self.refillTrigger == None:
			return
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Attempting to refill {0}'s effect:".format(self.card.name))
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print(self.effect)
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Our refill trigger is {0}.".format(self.refillTrigger))
		if trigger != TRIGGER_TYPES[self.refillTrigger]:
			return
		self.amount += 1
		if self.amount > self.maxAmount:
			self.amount = self.maxAmount
		if ACTIVE_DEBUG_STATES[DEBUG_STATES.effects]: print("Our new amount for this effect on {0} is {1}.".format(self.card.name, self.amount))

player1CardList = [
	"SkullBeast",
	"SkullBeast",
	"SkullBeast",
	"SoulConversion",
	"SoulConversion",
	"GhostlyGrasp",
	"GhostlyGrasp",
	"GhostlyGrasp",
	"SonataSilence",
	"SonataSilence",
	"SonataSilence",
	"DemonicProcession",
	"DemonicProcession",
	"DemonicProcession",
	"LadyGrey",
	"LadyGrey",
	"LadyGrey",
	"Jackshovel",
	"Jackshovel",
	"Gremory",
	"Gremory",
	"Gremory",
	"GhastlyAssault",
	"Minthe",
	"Minthe",
	"Minthe",
	"SarcophagusWraith",
	"SarcophagusWraith",
	"SarcophagusWraith",
	"PathPurgatory",
	"PathPurgatory",
	"DeathlyTyrant",
	"DeathlyTyrant",
	"DeathlyTyrant",
	"DeathsMistress",
	"DeathsMistress",
	"DeathsMistress",
	"Guilt",
	"Guilt",
	"Guilt"
]

player1 = Player("Jasper", player1CardList)
player2CardList = player1CardList
player2 = Player("Devin", player2CardList)

cardbuilder = CardBuilder()
game = Gameplay([player1, player2])
logic = Logic()

game.startGame()