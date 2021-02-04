# Exception for when we cannot find a cell labelled "Date"
# Error 201
class NoDateCellError(Exception):
	pass


# Exception for when some item under the "Date" column is not a date
# Arguments: index (COUNT STARTS AT "DATE" CELL AND GOES DOWN) and contents of the cell that was not a valid date
# Error 202
class InappropriateDateColumnError(Exception):
	def __init__(self, index, contents):
		self.index = index
		self.contents = str(contents)


# Exception for when we cannot find the players in the excel spreadsheet
# Error 203
class PlayersNotFoundError(Exception):
	pass

# Error 204
class MissingStatError(Exception):
	def __init__(self, playerName):
		self.playerName = playerName

# Error 205
class EmptyDateColumnError(Exception):
	pass

# Error 206
class UnchronologicalDateColumnError(Exception):
	def __init__(self, date1, date2):
		self.date1 = date1
		self.date2 = date2



