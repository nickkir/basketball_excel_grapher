import datetime
import numpy as np
import numbers
import graphingExceptions as gpe
import julian
from scipy.stats import pearsonr
from calendar import monthrange


# For representing "counting" stats. ex: number of wins, number of 3s made...
class RawStat:
	def __init__(self, statName):
		self.numName = statName

	# Returns a list of the names of all the components, in the order they need to be passed to computeValue() method
	def getOrderedListComponents(self):
		return [self.numName]

	def getName(self):
		return self.numName

	# Implements the computation strategy
	# Only works if the list is in the appropriate order
	@staticmethod
	def computeValue(intList):
		assert len(intList) == 1
		return intList[0]

	# Gets the symbol representing the nature of the stat in question
	@staticmethod
	def getTypeSymbol():
		return "#"


# For representing stats that are a ratio of two counting stats. ex: W/L ratio, 3-pt % ...
class RatioStat:

	def __init__(self, numName, denomName):
		self.numName = numName
		self.denomName = denomName

	# Returns a list of the names of all the components, in the order they need to be passed to computeValue() method
	def getOrderedListComponents(self):
		return [self.numName, self.denomName]

	def getName(self):
		return self.numName + "/" + self.denomName

	# Implements the computation strategy
	# Only works if the list is in the appropriate order
	@staticmethod
	def computeValue(orderedIntList):
		assert len(orderedIntList) == 2
		if orderedIntList[1] == 0:
			return 0
		return orderedIntList[0] / orderedIntList[1]

	# Gets the symbol representing the nature of the stat in question
	@staticmethod
	def getTypeSymbol():
		return "%"


# For representing a datapoint in a GRAPH
# We do this to store additional info to the actual value
# ex: it might be useful to know how many shots a 75% 3-point shooter has taken
class DataPoint:
	def __init__(self, aStat, orderedComponentValues, xValue):
		self.specificStat = aStat
		self.yValue = aStat.computeValue(orderedComponentValues)
		self.xValue = xValue
		self.breakdownDict = {}

		component_name_list = aStat.getOrderedListComponents()
		assert len(component_name_list) == len(orderedComponentValues)
		for i in range(len(component_name_list)):
			self.breakdownDict[component_name_list[i]] = orderedComponentValues[i]

	def getDetailedBreakdownDict(self):
		return self.breakdownDict

	def getYValue(self):
		return self.yValue

	def getXValue(self):
		return self.xValue

	# Creates a explanatory string based on all the attributes of the datapoint
	def getAnnotationString(self):
		result = ""
		breakdown = self.getDetailedBreakdownDict()

		for stat in breakdown:
			result = result + str(stat) + ": " + str(breakdown[stat])
			result = result + "\n"

		result = result + "Date: " + str(self.getXValue())

		return result


# For representing a player
class Player:

	# You should only pass dataframes created by Extractor objects, since they guarantee the proper format
	def __init__(self, name, dataframe):
		self.name = name
		self.datedShotData = dataframe

	def getName(self):
		return self.name

	def getEntry(self, date, rawStat):
		tracked_components = self.getTrackedRawStatStrings()

		if tracked_components.count(rawStat) == 0:
			raise gpe.StatNotTrackedError(rawStat, self.getName())
		else:
			return self.datedShotData.at[date, rawStat]

	# Throws an exception if for for a given date, the components of the stat are not all of the same type
	# This is so the user doesn't forget to a stat
	# Ex: on a given day, I enter the 3PA but not the 3PM, which artificially penalizes the player by giving him 0 for that day
	def checkStatComplete(self, aStat):
		dates = self.datedShotData.index
		components = aStat.getOrderedListComponents()

		if len(components) == 1:
			return True

		entries = []

		for date in dates:
			temp = []

			for component in components:
				temp.append(self.getEntry(date, component))

			entries.append(temp)

		for i in range(len(entries)):
			if not Helper.isUniformList(entries[i]):
				raise gpe.IncompleteRatioStatError(aStat.getName(), self.getName(), dates[i])


	# Returns a list of points that are either number or nan
	# List corresponds to grouped points for a player's raw stat in the spreadsheet
	def getGroupedRawStatValues(self, interval, rawStatName):
		assert interval > 0
		player_component_list = self.datedShotData.columns.values

		# Throws exception if we request a stat that is not being tracked on player
		if player_component_list.tolist().count(rawStatName) == 0:
			raise gpe.StatNotTrackedError(rawStatName, self.getName())

		# Groups the dates into blocks specified by interval
		grouped_dates_list = Helper.groupDates(self.datedShotData.index, interval) 

		output = []

		for period in grouped_dates_list:
			# Will contain strings, chars, nans ... i.e. whatever was found in the spreadsheet
			raw_data_point_list = []
			for date in period:
				raw_data_point_list.append(self.datedShotData.at[date, rawStatName])
			valid_data_points = Helper.stripNonNumbers(raw_data_point_list)

			if len(valid_data_points) == 0:
				output.append(np.nan)
			else:
				output.append(sum(valid_data_points))

		return output

	# Returns a list of points that are either numbers or nan
	# Each entry is the monthly total for the specified stat
	def getMonthlyRawStatValues(self, rawStatName):
		player_component_list = self.datedShotData.columns.values

		# Throws exception if we request a stat that is not being tracked on player
		if player_component_list.tolist().count(rawStatName) == 0:
			raise gpe.StatNotTrackedError(rawStatName, self.getName())

		grouped_dates_list = Helper.groupMonths(self.datedShotData.index)

		output = []

		for period in grouped_dates_list:
			# Will contain strings, chars, nans ... i.e. whatever was found in the spreadsheet
			raw_data_point_list = []
			for date in period:
				raw_data_point_list.append(self.datedShotData.at[date, rawStatName])
			valid_data_points = Helper.stripNonNumbers(raw_data_point_list)

			if len(valid_data_points) == 0:
				output.append(np.nan)
			else:
				output.append(sum(valid_data_points))

		return output

	# Returns a list of Datapoints 
	def getIntervalStatDatapoints(self, interval, desiredStat):
		# Before computing, check if the stat is complete
		self.checkStatComplete(desiredStat)

		component_name_list = desiredStat.getOrderedListComponents()

		x_labels = Helper.divideDates(self.datedShotData.index[0], self.datedShotData.index[-1], interval)

		stat_matrix = []

		for component_name in component_name_list:
			stat_matrix.append(self.getGroupedRawStatValues(interval, component_name))

		transformed_stat_entries = []

		for i in range(len(x_labels)):
			raw_ordered_component_values_list = []
			for column in stat_matrix:
				raw_ordered_component_values_list.append(column[i])
			transformed_stat_entries.append(DataPoint(desiredStat, raw_ordered_component_values_list, x_labels[i]))

		return transformed_stat_entries

	# Returns a list of floats, each element is the stat over that period
	# Similar to getIntervalStatDatapoints, but instead of datapoints we end up with floats
	def getIntervalStatValuesList(self, interval, desiredStat):
		# Before computing, check if the stat is complete
		self.checkStatComplete(desiredStat)

		component_name_list = desiredStat.getOrderedListComponents()

		stat_matrix = []

		for component_name in component_name_list:
			stat_matrix.append(self.getGroupedRawStatValues(interval, component_name))

		transformed_stat_entries = []

		for i in range(len(stat_matrix[0])):
			raw_ordered_component_values_list = []
			for column in stat_matrix:
				raw_ordered_component_values_list.append(column[i])
			transformed_stat_entries.append(desiredStat.computeValue(raw_ordered_component_values_list))

		return transformed_stat_entries

	# Returns a list of Datapoints, each entry is the Datapoint of a specific month
	def getMonthlyStatDatapoints(self, desiredStat):
		# Before computing, check if the stat is complete
		self.checkStatComplete(desiredStat)

		component_name_list = desiredStat.getOrderedListComponents()

		x_labels = []
		for date in self.datedShotData.index:
			month = date.month
			year = date.year
			day = monthrange(year, month)[1]
			monthly_label = datetime.datetime(year, month, day)
			if x_labels.count(monthly_label) == 0:
				x_labels.append(monthly_label)

		stat_matrix = []

		for component_name in component_name_list:
			stat_matrix.append(self.getMonthlyRawStatValues(component_name))

		transformed_stat_entries = []
		for i in range(len(x_labels)):
			raw_ordered_component_values_list = []
			for column in stat_matrix:
				raw_ordered_component_values_list.append(column[i])
			transformed_stat_entries.append(DataPoint(desiredStat, raw_ordered_component_values_list, x_labels[i]))

		return transformed_stat_entries

	# Returns a list of floats, where each entry is the value of the stat over a given month
	def getMonthlyStatValuesList(self, desiredStat):
		# Before computing, check if the stat is complete
		self.checkStatComplete(desiredStat)

		component_name_list = desiredStat.getOrderedListComponents()

		stat_matrix = []

		for component_name in component_name_list:
			stat_matrix.append(self.getMonthlyRawStatValues(component_name))

		transformed_stat_entries = []
		for i in range(len(stat_matrix[0])):
			raw_ordered_component_values_list = []
			for column in stat_matrix:
				raw_ordered_component_values_list.append(column[i])
			transformed_stat_entries.append(desiredStat.computeValue(raw_ordered_component_values_list))

		return transformed_stat_entries

	# Delegates call based on if we pass an int, "Weekly", or "Monthly"
	def getGroupedDatapoints(self, interval, stat):
		if interval == "Monthly":
			return self.getMonthlyStatDatapoints(stat)
		elif interval == "Weekly":
			return self.getIntervalStatDatapoints(7, stat)
		else:
			return self.getIntervalStatDatapoints(interval, stat)

	# Returns a list of objects which represent the stats being tracked for the desired player
	def getTrackedRawStats(self):
		output = []
		for statName in self.datedShotData.columns.values:
			output.append(RawStat(statName.upper()))
		return output

	def getTrackedRawStatStrings(self):
		output = []
		stat_objects = self.getTrackedRawStats()

		for stat_obj in stat_objects:
			output.append(stat_obj.getName())

		return output

	# Computes a raw stat over a desired period
	# @pre: the dates in the player's dataframe must be in order
	def getRawStatOverPeriod(self, statName, startDate, endDate):
		all_dates = self.datedShotData.index
		end_date_found = False
		relevant_dates = []

		if statName not in self.datedShotData.columns.values:
			raise gpe.StatNotTrackedError(statName, self)

		# Starting at to back just to increase efficiency
		for date in reversed(all_dates):
			if (endDate - date).days >= 0 and not end_date_found:
				end_date_found = True
				relevant_dates.append(date)
			elif (date - startDate).days < 0:
				break
			elif end_date_found:
				relevant_dates.append(date)
			else:
				continue

		relevant_dates.reverse()

		period_sum = 0
		num_practices = 0
		added = False
		for date in relevant_dates:
			entry = self.datedShotData.at[date, statName]
			if isinstance(entry, numbers.Number) and not np.isnan(entry):
				added = True
				period_sum += entry
				num_practices += 1

		if added:
			return period_sum
		else:
			return np.nan

	# Returns a float representing a stat between the start date and end date
	def getStatOverPeriod(self, stat, startDate, endDate):
		self.checkStatComplete(stat)
		ordered_component_names = stat.getOrderedListComponents()

		ordered_component_values = []
		for raw_name in ordered_component_names:
			ordered_component_values.append(self.getRawStatOverPeriod(raw_name, startDate, endDate))

		return stat.computeValue(ordered_component_values)

	# Returns an estimate for the POPULATION variance of the requested stat
	# Uses each practice as a random variable
	def getPopVariance(self, desiredStat):
		self.checkStatComplete(desiredStat)
		stat_components = desiredStat.getOrderedListComponents()
		matrix = []

		for aStat in stat_components:
			matrix.append(self.datedShotData[aStat])

		computed_stat_entries = []
		for i in range(len(matrix[0])):
			practice_entries = []
			for column in matrix:
				practice_entries.append(column[i])
			computed_stat_entries.append(desiredStat.computeValue(practice_entries))
			practice_entries.clear()

		computed_stat_entries = Helper.stripNonNumbers(computed_stat_entries)
		array = np.asarray(computed_stat_entries)
		return np.var(array, ddof=1)

	# Moving average of the specified stat, where the number of points in each average is n
	# Removes all the non number elements before conducting the moving average
	def getMovingAverageValuesList(self, desiredStat, n):
		self.checkStatComplete(desiredStat)
		stat_components = desiredStat.getOrderedListComponents()
		matrix = []

		tracked_stat_strings = self.getTrackedRawStatStrings()

		for aStat in stat_components:
			if tracked_stat_strings.count(aStat) > 0:
				matrix.append(self.datedShotData[aStat])
			else:
				raise gpe.StatNotTrackedError(aStat, self.getName())

		computed_stat_entries = []
		for i in range(len(matrix[0])):
			practice_entries = []
			for column in matrix:
				practice_entries.append(column[i])
			computed_stat_entries.append(desiredStat.computeValue(practice_entries))
			practice_entries.clear()

		computed_stat_entries = Helper.stripNonNumbers(computed_stat_entries)
		array = np.asarray(computed_stat_entries)

		if n > len(array):
			n = len(array)

		ret = np.cumsum(array, dtype=float)
		ret[n:] = ret[n:] - ret[:-n]
		return ret[n - 1:] / n

	# Returns a list of tuples of the form (Date, Float) which represent (Last date of moving average, average of the n practices)
	def getMovingAverageTuplesList(self, desiredStat, n):
		stat_components = desiredStat.getOrderedListComponents()

		date_stats_tuples_list = []

		tracked_stats_names = self.getTrackedRawStatStrings()

		for date in self.datedShotData.index:
			original = []
			for component in stat_components:
				if tracked_stats_names.count(component) > 0:
					original.append(self.datedShotData.at[date, component])
				else:
					raise gpe.StatNotTrackedError(component, self.getName())

			stripped = Helper.stripNonNumbers(original)
			if len(stripped) == len(original):
				date_stats_tuples_list.append((date, desiredStat.computeValue(original)))
			elif len(stripped) != 0:
				raise gpe.IncompleteRatioStatError(desiredStat.getName(), self.getName(), date)

		if len(date_stats_tuples_list) < n:
			n = len(date_stats_tuples_list)

		output = []
		for i in range(len(date_stats_tuples_list)-n+1):
			total = 0
			for j in range(n):
				total += date_stats_tuples_list[i+j][1]
			entry_date = date_stats_tuples_list[i+n-1][0]
			value = total / n
			output.append((entry_date, value))

		return output

	# Similar to the getGroupedRawStat, but does not perform the date grouping internally
	# This is so that computing averages can go faster
	def getRawStatValuesFromGroupedDates(self, rawStatName, groupedDateList):
		output = []

		tracked_stat_names = self.getTrackedRawStatStrings()
		if tracked_stat_names.count(rawStatName) == 0:
			raise gpe.StatNotTrackedError(rawStatName, self.getName())

		for period in groupedDateList:
			temp = []
			for date in period:
				temp.append(self.datedShotData.at[date, rawStatName])
			temp = Helper.stripNonNumbers(temp)

			# If there were no entries, we append np.nan
			if len(temp) == 0:
				output.append(np.nan)
			else:
				output.append(sum(temp))

		return output

	# Similar to the getGroupedStat, but does not perform the date grouping internally
	# This is so that computing averages can go faster
	def getStatValuesFromGroupedDates(self, desiredStat, groupedDatesList):

		# Before computing, check if the stat is complete
		self.checkStatComplete(desiredStat)

		matrix = []

		for component in desiredStat.getOrderedListComponents():
			matrix.append(self.getRawStatValuesFromGroupedDates(component, groupedDatesList))

		output = []

		for i in range(len(matrix[0])):
			temp = []
			for column in matrix:
				temp.append(column[i])

			output.append(desiredStat.computeValue(temp))

		return output

	# returns correlation coefficient of the specified stat, with respect to time
	def getCorrelationToTime(self, desiredStat):
		tuples_list = self.getMovingAverageTuplesList(desiredStat, 1)
		julian_dates = []
		values = []
		for (regular_date, value) in tuples_list:
			values.append(value)
			julian_dates.append(julian.to_jd(regular_date))

		julian_dates_array = np.asarray(julian_dates)
		values_array = np.asarray(values)

		return pearsonr(julian_dates_array, values_array)[0]


# CURRENTLY UNUSED, BUT MIGHT CHANGE LATER
class TableValueEntry:
	def __init__(self, value, descriptionDict):
		self.value = value
		self.description = descriptionDict

	def getValue(self):
		return self.value

	def getDescriptionString(self):
		return str(self.description)


class TeamInfo:

	def __init__(self, extractor):

		rawStatHolder = []
		uniqueRawStatsList = extractor.getUniqueRawStatNamesList()
		for rawStatName in uniqueRawStatsList: 
			rawStatHolder.append(RawStat(rawStatName))
		self.rawStats = rawStatHolder

		suggestionsHolder = []
		ratioTuplesList = extractor.getSuggestedRatioStatNameTuplesList()
		for nameTuple in ratioTuplesList:
			if len(nameTuple) == 2:
				suggestionsHolder.append(RatioStat(nameTuple[0], nameTuple[1]))
			else:
				suggestionsHolder.append(RawStat(nameTuple))
		self.suggestions = suggestionsHolder

		self.practiceDates = extractor.getDatesList()

		playerHolder = []
		playerNamesList = extractor.getPlayersList()
		for playerName in playerNamesList:
			playerHolder.append(Player(playerName, extractor.getDataFrameForPlayer(playerName)))

		self.roster = playerHolder

	def getRawStats(self):
		return self.rawStats

	def getSuggestedStats(self):
		return self.suggestions

	def getPracticeDates(self):
		return self.practiceDates

	def getRoster(self):
		return self.roster

	def getPlayerByName(self, playerName):
		for player in self.roster:
			if playerName.lower() == player.getName().lower():
				return player
		return None

	# Returns an ordered list based on the value of the requested stat over the requested period
	# Each element is a tuple of the form (player, value)
	def getRankedList(self, stat, startDate, endDate):
		roster = self.getRoster()
		output = []

		for player in roster:
			try:
				output.append((player, player.getStatOverPeriod(stat, startDate, endDate)))
			except gpe.StatNotTrackedError:
				output.append((player, np.nan))

		return Helper.sortNANList(output)

	# Returns a number representing the team's average between the start date and end date
	# returns np.nan if there are no entries for the period in question
	def getAverageOverPeriod(self, stat, startDate, endDate):
		ranked_list = self. getRankedList(stat, startDate, endDate)
		num_entries = len(ranked_list)
		cumulative = 0
		added = False

		for (player, value) in ranked_list:
			if np.isnan(value):
				num_entries -= 1
			else:
				cumulative += value
				added = True

		if added:
			return cumulative/num_entries
		else:
			return np.nan


class NullTeamInfo:
	def getRawStats(self):
		return []

	def getSuggestedStats(self):
		return []

	def getPracticeDates(self):
		return []

	def getRoster(self):
		return []


# Class for miscellaneous helper functions
# Should not be instantiated or used by external classes
class Helper:
	# returns a list of dates, each of which is (exclusive) end of the previous interval
	@staticmethod
	def divideDates(startDate, endDate, interval):
		assert interval > 0
		output = []

		date_pointer = startDate

		while((endDate - date_pointer).days >= 0):
			date_pointer = date_pointer + datetime.timedelta(days=interval)
			output.append(date_pointer)

		return output

	# returns a matrix of dates, each column is the dates grouped by interval
	# ex : [day1, day2, day3, day4] -> [[day1, day2], [day3], [day4]]
	# If there are no dates in a certain interval, we still append an empty list
	@staticmethod
	def groupDates(dateList, interval):

		if interval == "Monthly":
			return Helper.groupMonths(dateList)
		elif interval == "Weekly":
			interval = 7

		assert interval > 0

		# Container for result
		grouped_dates = []

		# List of divisions
		list_cutoffs = Helper.divideDates(dateList[0], dateList[-1], interval)
		interval_start_date_index = 0

		for endpoint in list_cutoffs:
			dates_before_endpoint = []

			for i in range(interval_start_date_index, len(dateList)):
				current_date = dateList[i]
				if (endpoint - current_date).days > 0:
					dates_before_endpoint.append(current_date)
				else:
					interval_start_date_index = i
					grouped_dates.append(dates_before_endpoint)
					break

		# We need to append the last portion, since we never enter the else block
		grouped_dates.append(dates_before_endpoint)
		return grouped_dates

	# Returns a matrix of dates, each row is all the dates in a particular month
	@staticmethod
	def groupMonths(dateList):
		result = []

		current_month = dateList[0].month
		current_year = dateList[0].year
		current_grouping = []
		for date in dateList:
			if date.month == current_month and date.year == current_year:
				current_grouping.append(date)
			else:
				result.append(current_grouping.copy())
				current_month = date.month
				current_year = date.year
				current_grouping.clear()
				current_grouping.append(date)

		result.append(current_grouping)

		return result

	# Returns a list that contains only the numbers from the list argument
	@staticmethod
	def stripNonNumbers(aList):
		stripped_list = []
		for item in aList:
			if (isinstance(item, numbers.Number) and not np.isnan(item)):
				stripped_list.append(item)

		return stripped_list

	# Sorts a list of (player, value) in decreasing order based on value, but sticks all the np.nan values at the back
	@staticmethod
	def sortNANList(aList):
		real_values_list = []
		nan_list = []

		for entry in aList:
			if np.isnan(entry[1]):
				nan_list.append(entry)
			else:
				real_values_list.append(entry)

		real_values_list.sort(key=lambda x: x[1])
		real_values_list.reverse()

		return (real_values_list + nan_list)

	@staticmethod
	def isANumber(x):
		return isinstance(x, numbers.Number) and not np.isnan(x)

	# Take a list of dates and values
	# If the a given value is not a float, we remove both it and its respective date from the appropriate list
	@staticmethod
	def cleanUpForCorrelation(date_list, value_list):
		assert len(date_list) == len(value_list)

		new_dates = []
		new_values = []

		for i in range(len(value_list)):
			if Helper.isANumber(value_list[i]):
				new_values.append(value_list[i])
				new_dates.append(date_list[i])

		return (new_dates, new_values)

	# Distinguishes between three types: Numbers(floats or integers) and Non-Numbers(np.nan, strings...)
	# Returns a boolean based on those types
	@staticmethod
	def areSameType(item1, item2):

		item1_is_num = False
		item2_is_num = False

		if isinstance(item1, numbers.Number):
			item1_is_num = not np.isnan(item1)

		if isinstance(item2, numbers.Number):
			item2_is_num = not np.isnan(item2)

		return item1_is_num == item2_is_num

	# Given a list, returns true if all the elements are numbers (floats, integers) or all the elements are non-numbers (np.nan, strings...)
	@staticmethod
	def isUniformList(cellList):
		assert len(cellList) > 0

		for item in cellList:
			if Helper.areSameType(cellList[0], item):
				continue
			else:
				return False

		return True


class GraphDataContainer:
	def __init__(self, playersList, interval, stat, team):
		self.players = playersList
		self.interval = interval
		self.stat = stat
		self.team = team

	# Returns a matrix, each entry is a player's datapoints
	def getAllYSeries(self):
		output_matrix = []
		for player in self.players:
			output_matrix.append(player.getGroupedDatapoints(self.interval, self.stat))

		return output_matrix

	# Returns a list of the x-axis labels for the specified graph
	# NEEEEED TO FIX because player may not have dummy stat
	def getXSeries(self):
		dummy_player = self.team.getRoster()[0]
		dummy_stat = dummy_player.getTrackedRawStats()[0]
		dummy_dps = dummy_player.getGroupedDatapoints(self.interval, dummy_stat)

		output = []
		for dp in dummy_dps:
			output.append(dp.getXValue())

		return output

	# Returns a list of VALUES (NOT DATAPOINTS), which represent the selected players average
	# NEEEEEEEEEEEEED TO FIX
	def getSelectedPlayersAverage(self):
		assert not len(self.players) == 0
		average_values_list = []
		for i in range(len(self.getXSeries())):
			total = 0
			for player in self.players:
				player_entry = player.getGroupedDatapoints(self.interval, self.stat)[i].getYValue()
				if not np.isnan(player_entry):
					total += player_entry
			average_values_list.append(total/len(self.players))

		return average_values_list

	# Gets the average of the team
	# Throws a stat not tracked exception if the stat is not available for a certain player
	def getTeamAverage(self):
		all_players = self.team.getRoster()

		grouped_dates = Helper.groupDates(self.team.getPracticeDates(), self.interval)

		all_entries = []

		for player in all_players:
			try:
				all_entries.append(player.getStatValuesFromGroupedDates(self.stat, grouped_dates))
			except gpe.StatNotTrackedError:
				continue

		average = []
		for i in range(len(all_entries[0])):
			temp = 0
			num_players = len(all_entries)
			for column in all_entries:
				if np.isnan(column[i]):
					num_players -= 1
				else:
					temp += column[i]

			if num_players == 0:
				average.append(np.nan)
			else:
				average.append(temp/num_players)

		return average

	def getSelectedPlayerNamesOrdered(self):
		result = []
		for player in self.players:
			result.append(player.getName())

		return result


