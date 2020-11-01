import numpy
from collections import namedtuple
Point = namedtuple('point', ('x', 'y'))

def get_peaks(data):
	peakSearchPattern = [-1,-1,1,1]  # negative slope, negative slope, positive slope, positive slope
	diffData=numpy.diff(data)
	
	possiblePeaks={}
	try:
		#import pdb;pdb.set_trace()
		for i in range(len(diffData)):
			if abs(diffData[i])<400:  # TODO make this threshold easily adjustable ??
				continue
			vals = [diffData[i+j] for j in range(len(peakSearchPattern))]
			assert len(vals)==len(peakSearchPattern)
			counter = 0
			for element, value in zip(peakSearchPattern, vals):
				if element==1 and value>0:
					counter += 1
				elif element==-1 and value<0:
					counter += 1
				elif element==0 and value == 0:
					counter += 1
				#print(element, value, counter)
			if counter==len(peakSearchPattern):
				
				x = i+(len(peakSearchPattern)//2)
				possiblePeaks[x]=diffData[i]
				print('peak x{} y{}'.format(x, diffData[i]))
			# print('\n')
	except IndexError:
		pass
	return possiblePeaks
