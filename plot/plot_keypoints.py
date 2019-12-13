import pandas as pd
import matplotlib.pyplot as plt
import sys
import re
import string
import numpy as np
from itertools import cycle
from matplotlib.patches import Polygon
from scipy import stats

__author__ = "Lygerakis Fotios"
__license__ = "GPL"
__email__ = "ligerfotis@gmail.com"

title = "Index-Thumb Groundtruth With Covered Thumb"

#box plot aperture set
top = 15
bottom = 0	

# froundtruth printed on the scatter plot
gt_point_index = [-0.2, 0.07]
gt_point_thumb = [-0.25, 0]

# axes ranges
axis_range_x = [-0.4, 0.00]
axis_range_y = [-0.2, 0.2]

# steps for tick printing on the axes
step_x = .01
step_y = .01

# used in boxplot | positioned under each box
aperture_size = ['5cm', '4cm', '3cm', '2cm']
msgsPerFile = ["177", "173", "201", "196"]
img_raw_msgs = ["178", "176", "206", "200"]
pc_msgs = ["180", "174", "204", "198"]
# aperture_size = ['5cm', '10cm', '15cm']
# msgsPerFile = ["141", "99", "125"]
# img_raw_msgs = ["146", "101", "129"]
# pc_msgs = ["142", "100", "125"]

# the z score value used to filter outliers
zscore = 2.698

def blacklist():
	blacklist_x = np.array([-0.153134927441, -0.180600002403, -0.238413722605, -0.194435179098])
	blacklist_y = np.array([0.929576465814, 0.986484451679, 0.0289434800859, 0.0676014466519])
	return blacklist_x, blacklist_y

# Function to extract all the distinct keypoints from a csv 
def getKeyPoints(columns): 
	columns = string.join(columns)
	array = re.findall(r"/topic_transform/keypoints/[0-9]+/points/point/x", columns)
	return array 

# Function to extract all the distinct keypoint names from a csv 
def getKeypointNames(df): 
	listOfNames = []
	for col in df.columns[1:]:
		if "name" in col:
			listOfNames.append(df[col].loc[0])
	return listOfNames

def get_cmap():
    return cycle('brgcmk')

def removeBlacklist(df, listOfKeyPoints_x, listOfKeyPoints_y, listOfKeyPoints_z, new_listOfNames):
	b_list = blacklist()

	for point_x in listOfKeyPoints_x:
		df.drop(df.loc[df[point_x].isin(np.around(b_list[0], decimals=7))].index, inplace=True)

	for point_y in listOfKeyPoints_y:
		df.drop(df.loc[df[point_y].isin(np.around(b_list[1], decimals=7))].index, inplace=True)

	return df, listOfKeyPoints_x, listOfKeyPoints_y, listOfKeyPoints_z, new_listOfNames


def keypointExtractor(filename, withOutliers):
	df = pd.read_csv(filename)
	
	listOfNames = getKeypointNames(df)
	numOfKeyPoints = len(getKeyPoints(df.columns))

	listOfKeyPoints_x = ["/topic_transform/keypoints/" + str(i) + "/points/point/x" for i in range(numOfKeyPoints)]
	listOfKeyPoints_y = ["/topic_transform/keypoints/" + str(i) + "/points/point/y" for i in range(numOfKeyPoints)]
	listOfKeyPoints_z = ["/topic_transform/keypoints/" + str(i) + "/points/point/z" for i in range(numOfKeyPoints)]

	new_listOfKeyPoints_x, new_listOfKeyPoints_y, new_listOfKeyPoints_z = [], [], []
	new_listOfNames = []
	# create new dataframe containing only columns with point information 
	new_df = pd.DataFrame()
	for i, point_list_names in enumerate(zip(listOfKeyPoints_x, listOfKeyPoints_y, listOfKeyPoints_z)):
		# check if keypoint contains mostly zero points
		count_valid_array = [(df[col_point]!=0).sum() for col_point in point_list_names]

		if all([point > numOfKeyPoints/4 for point in count_valid_array]):
			new_listOfKeyPoints_x.append(point_list_names[0])
			new_listOfKeyPoints_y.append(point_list_names[1])
			new_listOfKeyPoints_z.append(point_list_names[2])
			new_listOfNames.append(listOfNames[i])

			for col in point_list_names:
				# rounding is crucial for comparing
				new_df[col] = df[col].astype(float).round(7)

	# replace zero values with NAN so they do not plot
	new_df.replace(0, np.nan, inplace=True)

	# remove outliers
	if not withOutliers:
		new_df = new_df[(np.abs(stats.zscore(new_df)) < zscore).all(axis=1)]

	return removeBlacklist(new_df, listOfKeyPoints_x, listOfKeyPoints_y, listOfKeyPoints_z, new_listOfNames)

def extractAperture(filename):
	df, new_listOfKeyPoints_x,new_listOfKeyPoints_y, new_listOfKeyPoints_z,_ = keypointExtractor(filename, withOutliers=True)

	# calculate aperture
	aperture = []
	point_list = []
	for keypoint_x, keypoint_y in zip(new_listOfKeyPoints_x, new_listOfKeyPoints_y):
		point_list.append([df[keypoint_x].values, df[keypoint_y].values])

	susbtraction_x = point_list[0][0] - point_list[1][0]
	substraction_y = point_list[0][1] - point_list[1][1]	

	# euclidean distance
	aperture = np.sqrt(np.add(np.power(susbtraction_x, 2), np.power(substraction_y,2)))
	aperture = aperture[~np.isnan(aperture)]

	return aperture

def boxPlot():

	filenames = sys.argv[2:]
	
	apertures = [extractAperture(filename) for filename in filenames]

	data_cm = [aperture * 100 for aperture in apertures] 

	labels = [ap+"\nTotal messages: "+msg for ap, msg in zip(aperture_size, msgsPerFile)]

	fig, ax = plt.subplots(figsize=(10, 6))
	fig.canvas.set_window_title('Aperture between Thumb and Index Fingertips in cm')
	

	medianprops = dict(linestyle=None, linewidth=0, color='white')
	bp = ax.boxplot(data_cm, notch=0, sym='+', vert=1, whis=1.5, showmeans=True, meanline=True, medianprops=medianprops)
	plt.setp(bp['boxes'], color='black')
	plt.setp(bp['whiskers'], color='black')
	plt.setp(bp['fliers'], color='red', marker='+')

	# Add a horizontal grid to the plot, but make it very light in color
	# so we can use it for reading data values but not be distracting
	ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
	               alpha=0.5)
	# Hide these grid behind plot objects
	ax.set_axisbelow(True)
	ax.set_title('Comparison of Aperture Discritability')
	ax.set_xlabel('Distripution')
	ax.set_ylabel('Aperture in cm')

	# Now fill the boxes with desired colors
	box_colors = ['darkkhaki', 'royalblue']
	num_boxes = len(data_cm)
	means = [np.mean(keypoint) for keypoint in data_cm]
	stds = [np.std(keypoint) for keypoint in data_cm]

	for i in range(num_boxes):
	    box = bp['boxes'][i]
	    boxX = []
	    boxY = []
	    for j in range(5):
	        boxX.append(box.get_xdata()[j])
	        boxY.append(box.get_ydata()[j])
	    box_coords = np.column_stack([boxX, boxY])
	    # Alternate between Dark Khaki and Royal Blue
	    ax.add_patch(Polygon(box_coords, facecolor=box_colors[i % 2]))
	# Set the axes ranges and axes labels
	ax.set_xlim(0.5, num_boxes + 0.5)

	plt.yticks(np.arange(bottom, top, 1))
	ax.set_xticklabels(labels, fontsize=8)

	plt.show()

def plot():
	try:
		filename = sys.argv[2]
	except:
		print("Invalid file name given")
		sys.exit()

	new_df, new_listOfKeyPoints_x,new_listOfKeyPoints_y, new_listOfKeyPoints_z, new_listOfNames = keypointExtractor(filename, withOutliers=False)
	new_df.to_csv("~/tmp.csv")

	fig, ax = plt.subplots(figsize=(10, 6))
	cmap = get_cmap()
	scat = None
	for i, (list_x, list_y) in enumerate(zip(new_listOfKeyPoints_x, new_listOfKeyPoints_y)):
		scat = plt.scatter(new_df[list_x], new_df[list_y], s=0.7, color=cmap.next(), label=new_listOfNames[i]) 

	fig.suptitle(title)
	ax.set_xlabel('x-axis (in m)')
	ax.set_ylabel('y-axis (in m)')

	plt.xticks(np.arange(axis_range_x[0], axis_range_x[1], step=step_x))
	plt.yticks(np.arange(axis_range_y[0], axis_range_y[1], step=step_y))

	ax.set_xlim(axis_range_x)
	ax.set_ylim(axis_range_y)

	mean_x = np.mean(new_df[new_listOfKeyPoints_x])
	mean_y = np.mean(new_df[new_listOfKeyPoints_y])
	std_x = np.std(new_df[new_listOfKeyPoints_x])
	std_y = np.std(new_df[new_listOfKeyPoints_y])

	# get two gaussian random numbers, mean=0, std=1, 2 numbers
	gt_points_x = [gt_point_index[0], gt_point_thumb[0]]
	gt_points_y = [gt_point_index[1], gt_point_thumb[1]]

	plt.scatter(gt_points_x, gt_points_y, s=15, color=cmap.next())

	ax.annotate("Ground Truth \nThumb Tip", (gt_points_x[0], gt_points_y[0]))
	ax.annotate("Ground Truth \nIndex Tip", (gt_points_x[1], gt_points_y[1]))

	plt.errorbar(mean_x, mean_y,  markersize='2',fmt='o', color='black', ecolor='black', ms=20,  mfc='white',label="Mean")

	ax.minorticks_on()
	ax.grid(which='major', linestyle='-', linewidth='0.5', color='black')
	ax.grid(which='minor', linestyle=':', linewidth='0.5', color='black')
	
	ax.legend(markerscale=5)
	plt.show()

if __name__== "__main__":
	if sys.argv[1] == "boxplot":
		boxPlot()
	elif sys.argv[1] == "plotkeypoints":
		plot()
	else:
		print("Wrong keyword.")
		print("Select \"boxplot\" or \"plotkeypoints\".")