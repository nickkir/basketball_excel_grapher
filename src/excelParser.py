import pandas as pd 
import numpy as np
import fileParsingExceptions as fpe
import numbers
import datetime


# This will be a concrete class that will concretely implement a future interface
# This spreadsheet validation might not work perfectly in practice, so I want to be able to change it moving forward
class ExcelParser1:

	# Creates an object whose only attribute is a dataframe object, which is created by the read_excel method from the pandas module
	# Throws PermissionError, FileNotFoundError
	def __init__(self, filepath):
		self.df = pd.read_excel(filepath)
		self.trim()

	# Finds the cell labeled "Date", and returns its position in the DATAFRAME as a tuple
	# If no such cell exists, it throws the ExcelValidator.NoDateCellError Exception
	def findDate(self):
		# Starts by scanning the contents of the data frame
		(num_rows, num_cols) = self.df.shape
		for col_pointer in range(num_cols):
			for row_pointer in range(num_rows):
				if type(self.df.iat[row_pointer, col_pointer]) == str and self.df.iat[row_pointer, col_pointer].lower().startswith("date"):
					return (row_pointer, col_pointer)

		# Check the indexes of the columns for the date cell, which will return (-1, column_index)
		# This would mean the the spreadsheet is incorrectly formatted, but we want to be able to locate the exact cause
		col_idexes = self.df.columns.values
		for cell in col_idexes:
			if type(cell) == str and cell.lower().startswith("date"):
				return (-1, self.df.columns.get_loc(cell))

		#If the "date" cell is not present, then finally raise the exception
		raise fpe.NoDateCellError() 

	# Returns a list of all dates in the "date" column
	# Will get anything that is a Timestamp object, or that can be parsed into a Timestamp object (and will perform the parsing)
	# If one entry is not a date, raises InappropriateDateColumnError
	def getDatesList(self):

		result = []
		(title_row, title_col) = self.findDate()

		(num_row, num_col) = self.df.shape  # num_rows includes the title row

		for row_pointer in range(title_row + 1, num_row): # We don't substract 1 since num_row = index of last row + 1 (This is because the first row has index 0)
			current_cell = self.df.iat[row_pointer, title_col]
			# If the cell is empty, then we throw an exception
			if pd.isnull(current_cell):
				raise fpe.InappropriateDateColumnError(row_pointer+2, current_cell)

			# If the current cell is a Timestamp object, add it to the output
			elif isinstance(current_cell, datetime.datetime):
				result.append(current_cell)
			else: 
				# Even if we do not have a Timestamp object, we can try to see if it is in a parsable form
				try:
					result.append(pd.Timestamp(current_cell))
				except:
					raise fpe.InappropriateDateColumnError(row_pointer+2, current_cell)

		if len(result) == 0:
			raise fpe.EmptyDateColumnError

		HelperToolKit.datesInOrder(result)

		return result

	# Returns the index of the row where the player names are situated
	# If the names are amongst the column keys, we return -1
	# Raises PlayersNotFoundError if no rows contain any strings
	# Srategy: start by checking the column titles for strings not containing "Unnamed:", then we can stop. Otherwise, loop through the rows of the table
	def getPlayerRowIndex(self):
		# We don't want to consider the "date" columns as having any potential names, so remove all columns up to and including the date
		# Note that .drop doesn't modify the dataframe itself, but rather, returns a new dataframe with the desired column removed
		(date_row, date_col) = self.findDate()
		labels_to_drop = []
		for counter in range(date_col+1):
			labels_to_drop.append(self.df.columns[counter])
		truncated_df = self.df.drop(labels_to_drop, axis=1)

		strings_on_current_row = []
		# This will return the first row of the spreadsheet, regardless of whether or not its empty
		# We will check if there any strings in here, and if not, make our way down the sheet
		titles = truncated_df.columns
		for cell in titles:
			if not cell.startswith('Unnamed:'):
				strings_on_current_row.append(cell)

		# If the first row had strings, we return a list of each string on it
		if not len(strings_on_current_row) == 0:
			return -1

		# If not, we make our way down the rows
		else:
			i = 0
			for(index, series) in truncated_df.iterrows():
				for item in series.values:
					if type(item) == str:
						strings_on_current_row.append(item)
				if not len(strings_on_current_row) == 0:
					return i
				else:
					i += 1

		# If no rows contained strings, raise an exception
		raise fpe.PlayersNotFoundError()

	# Returns the list of players
	# Throws PlayersNotFoundError()
	def getPlayersList(self):
		(date_row, date_col) = self.findDate()
		player_row_index = self.getPlayerRowIndex()

		# If the player row and the stat row have the same index, that means we mistook the stats as playernames, and throw PlayersNotFoundError
		if date_row == player_row_index:
			raise fpe.PlayersNotFoundError()

		if player_row_index == -1:
			player_row = self.df.columns
		else:
			player_row = self.df.iloc[player_row_index].values

		player_list = []
		for item in player_row:
			if type(item) == str and not item.startswith('Unnamed:'):
				player_list.append(item)

		return player_list

	# Returns a list of stat columns (i) 
	# Each element in the list is an array, whose first element is the stat in question
	# Elements are in order they appear in spreadsheet, but have no name attached to them
	def getStatColumns(self):
		columns = []
		(date_row, date_col) = self.findDate()
		(num_row, num_col) = self.df.shape

		for col_index in range(date_col+1, num_col):
			columns.append(self.df.iloc[date_row:, col_index].values)

		return columns

	# Return a list of every unique stat being tracked in the spreadsheet (i.e. not every player necessarilly has a column with the stats in this list)
	# Returns the unique stats in an arbitrary order
	def getUniqueRawStatNamesList(self):
		# We don't want to consider the "date" columns as having any potential stats, so remove all columns up to and including the date
		# Note that .drop() doesn't modify the dataframe itself, but rather, returns a new dataframe with the desired column removed
		(date_row, date_col) = self.findDate()
		labels_to_drop = []
		for counter in range(date_col+1):
			labels_to_drop.append(self.df.columns[counter])
		truncated_df = self.df.drop(labels_to_drop, axis = 1)

		repeated_stats = truncated_df.iloc[date_row].values
		
		uppercase_stats = []
		for stat in repeated_stats:
			if type(stat) == str:
				uppercase_stats.append(stat.upper())
			elif not np.isnan(stat):
				uppercase_stats.append(stat)

		return list(set(uppercase_stats))

	# returns a list where each element is a tuple of the form (stat_name, values_list)
	def getOrderedDictForPlayer(self, playerName):
		# Make sure the desired player is in fact in the spreadsheet
		players = self.getPlayersList()
		assert (players.count(playerName) > 0)

		all_stat_cols = self.getStatColumns()
		player_row_index = self.getPlayerRowIndex()

		# We don't want to consider the "date" columns as having any potential names, so remove all columns up to and including the date
		# Note that .drop doesn't modify the dataframe itself, but rather, returns a new dataframe with the desired column removed
		(date_row, date_col) = self.findDate()
		labels_to_drop = []
		for counter in range(date_col+1):
			labels_to_drop.append(self.df.columns[counter])
		truncated_df = self.df.drop(labels_to_drop, axis=1)

		# Check if the players are the columns titles
		if player_row_index == -1:
			player_row = truncated_df.columns
		else:
			player_row = truncated_df.iloc[player_row_index].values
		
		# We know need to loop through the player rows to get all the relevant columns, so we initialize some tracking stuff
		# We get the index of the player we are working on, and once we reach the next player, we stop gathering columns
		# We add "Stop" to the player list just so we can apply this logic to the last player on the list
		player_index = players.index(playerName)
		players.append("Stop")
		end_cell = players[player_index+1]
		counter = 0
		found = False
		player_cols = []

		for item in player_row:
			if item == playerName:
				found = True
				player_cols.append(all_stat_cols[counter])
				counter += 1
			elif not found:
				counter += 1
			elif found and not (item == end_cell):
				player_cols.append(all_stat_cols[counter])
				counter += 1
			else:
				break

		output = []
		for col in player_cols:
			if type(col[0]) == np.float64 and np.isnan(col[0]):
				raise fpe.MissingStatError(playerName)
			output.append((str(col[0]).upper(),np.delete(col, 0)))

		return output

	# Returns a list of tuples of the form (string, string).
	# First component is the numerator stat name, second is the denominator stat name
	# If there is a odd number of stats, the last element of the list ill be a one-uple
	# Arbitrary order
	def getSuggestedRatioStatNameTuplesList(self):
		output = []

		rosterNames = self.getPlayersList()
		statsEachPlayer = []

		# Need the headers of each player
		for name in rosterNames:
			sudoDict = self.getOrderedDictForPlayer(name)
			temp = []
			for (stat, list) in sudoDict:
				temp.append(stat)
			statsEachPlayer.append(temp)

		# Pairing happens here
		for header in statsEachPlayer:
			header_length = len(header)
			for index in range(0, header_length, 2):
				if index == header_length - 1:
					output.append((header[index]))
				else:
					output.append((header[index], header[index+1]))

		uniques = set(output)
		output_list = []

		for stat in uniques:
			output_list.append(stat)

		return output_list

	def getDataFrameForPlayer(self, playerName):
		dates = self.getDatesList()
		sudoPlayerDict = self.getOrderedDictForPlayer(playerName)

		real_dict = {}

		for (stat_name, stat_values_list) in sudoPlayerDict:
			real_dict[stat_name] = stat_values_list

		playerDF = pd.DataFrame(data=real_dict, index=dates)

		return playerDF

	# Returns true if a column is unnamed and the cells all contain NaN
	def columnIsEmpty(self, colName):
		column = self.df.loc[:, colName]

		if not colName.startswith('Unnamed:'):
			return False

		for cell in column:
			if not isinstance(cell, numbers.Number):
				return False
			elif not np.isnan(cell):
				return False

		return True

	# If there is a completely empty row to the right of the dataframe, we remove that row ad everything past it
	# We also remove any empty rows at the start
	def trim(self):
		entered = False
		exited = False

		to_drop = []

		for column_header in self.df.columns.values:
			if self.columnIsEmpty(column_header) and not entered:
				to_drop.append(column_header)
			elif not self.columnIsEmpty(column_header) and not entered:
				entered = True
			elif entered and self.columnIsEmpty(column_header):
				exited = True

			if exited:
				to_drop.append(column_header)

		self.df = self.df.drop(columns=to_drop)


class HelperToolKit:
	@staticmethod
	def datesInOrder(datesList):
		for i in range(len(datesList)-1):
			if (datesList[i+1] - datesList[i]).days < 0:
				raise fpe.UnchronologicalDateColumnError(datesList[i], datesList[i+1])



