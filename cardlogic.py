import random
import enum
import json
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(THIS_FOLDER, 'cardlibrary.json')) as cardlibrary:
  library = json.load(cardlibrary)

# ENUMS
class ATTACK_STATES(enum.Enum):
	sickness = 1
	rush = 2
	storm = 3
	attacked = 4

class TRIGGER_TYPES(enum.Enum):
	onTurnStart = 1
	onCardInvoked = 2
	onCardDrawn = 3
	onCardDiscarded = 4
	onCardPlayed = 5
	onCardAttacking = 6
	onCardsClashed = 7
	onCardDied = 8
	onCardEvolved = 9
	onPlayerHealthChanged = 10
	onTurnEnd = 11

class CARD_TRIGGER_TYPES(enum.Enum):
	onDrawn = 1
	onPlayed = 2
	onAttacking = 3
	onClashing = 4
	onLeaderClashing = 5
	onDealtDamage = 6
	onTookDamage = 7
	onDied = 8
	onDiscarded = 9

# CARD CONSTRUCTOR
class CardBuilder:
	def __init__(self):
		x = 0

	def buildCard(self, cardName, owner):
		cardObj = library[0][cardName]
		card = None
		if cardObj["Type"] == "Monster":
			front = CardFace(cardObj["Front"]["Attack"], cardObj["Front"]["Defense"], [])
			attack = 2
			defense = 2
			if "AttackChange" in cardObj["Back"]:
				attack = cardObj["Back"]["AttackChange"]
			if "DefenseChange" in cardObj["Back"]:
				defense = cardObj["Back"]["DefenseChange"]
			back = CardFace(attack, defense, [])
			card = MonsterCard(cardObj["Name"], cardObj["Cost"], front, back, owner)
		return card

# CARD LITERALS
class Card:
	def __init__(self, name, cost, front, owner):
		self.name = name
		self.cost = cost
		self.front = front
		self.cardTriggers = CardTriggers()
		self.cardNum = game.getCardNum(owner)

	def toString(self):
		return self.name

	def registerAbility(self, ability):
		self.cardTriggers.addTrigger(ability.trigger, ability.effect, numActivations, kwargs)

class CardFace:
	def __init__(self, attack, defense, cardAbilities=[]):
		self.attack = attack
		self.defense = defense
		self.cardAbilities = cardAbilities

class SpellCard(Card):
	def __init__(self, name, cost, front, enhance=None):
		Card.__init__(name, cost, front, enhance)

	def print(self):
		print("{0}: {1} cost".format(self.name, self.cost))

	# def onPlay(self):

class MonsterCard(Card):
	def __init__(self, name, cost, front, back, owner):
		Card.__init__(self, name, cost, front, owner)
		self.facing = front
		self.back = back
		self.attack = None

	def onPlay(self):
		self.attack = self.front.attack
		self.defense = self.front.defense
		self.attackState = ATTACK_STATES.sickness

	def onPlayEnhance(self):
		self.attack = self.enhance.attack
		self.defense = self.enhance.defense

	def onEvolve(self):
		self.facing = self.back

		self.buff([self.attack.attack, self.attack.defense])

	def buff(self, buff):
		self.attack += buff[0]
		self.defense += buff[1]

	def print(self):
		if self.attack:
			print("{0}: {1} cost, {2}/{3}. {4}".format(self.name, self.cost, self.attack, self.defense, self.attackState))
		else :
			print("{0}: {1} cost, {2}/{3}".format(self.name, self.cost, self.front.attack, self.front.defense))

# TRIGGER SYSTEM
class CardTriggers:
	def __init__(self):
		self.triggers = {}
		for i in range(11):
			self.triggers[i] = []

	def addTrigger(self, triggerType, effect, numActivations, kwargs):
		self.triggers[triggerType] = effect

	def resolve(self, triggerType):
		for trigger in self.triggers[triggerType]:
			trigger.resolve()

class CardSpecifics:
	def __init__(self, **kwargs):
		self.kwargs = kwargs
		self.owner = None
		self.card = None

	def eval(self, card):
		# if self.kwargs.name not card.name:
		# 	return False
		# if self.kwargs.allied not (self.owner is card.owner)
		# 	return False

		return True

	def setOwner(self, player):
		self.owner = player

	def setCard(self, card):
		self.card = card

# ABILITIES
class CardAbility:
	def __init__(self, trigger, effect, numActivations=-1, **kwargs):
		self.trigger = trigger
		self.effect = effect
		self.numActivations = numActivations
		self.kwargs = kwargs

class LastWords(CardAbility):
	def __init__(self, effects):
		CardAbility.__init__(self, TRIGGER_TYPES.onCardDeath, effects)

class Fanfare(CardAbility):
	def __init__(self, effect, numActivations=-1):
		CardAbility.__init__(self, CARD_TRIGGER_TYPES.onPlayed, effect, numActivations)

class OnOtherDestroyed(CardAbility):
	def __init__(self, effects, specifics, numActivations=-1):
		CardAbility.__init__(self, TRIGGER_TYPES.onOtherDestroyed, effects, numActivations, { "cardSpecifics": specifics })

class UnionBurst(CardAbility):
	def __init__(self, effects, unionNum):
		CardAbility.__init__(self, TRIGGER_TYPES.onPlay, effects, { "unionNum": unionNum })

# EFFECTS
class Effect:
	def __init__(self):
		self.owner = None
		self.card = None

class GainShadowsEffect(Effect):
	def __init__(self, numShadows):
		Effect.__init__(self)
		self.numShadows = numShadows

	def resolve(self):
		self.owner.gainShadows(self.numShadows)

class BuffSelfEffect(Effect):
	def __init__(self, buff):
		Effect.__init__(self)
		self.buff = buff

	def resolve(self):
		self.card.buff(self.buff)

class StormEffect(Effect):
	def __init__(self):
		Effect.__init__(self)

	def resolve(self):
		self.card.attackState = ATTACK_STATES.stor