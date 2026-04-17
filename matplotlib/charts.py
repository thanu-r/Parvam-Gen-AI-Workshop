#bar chart

import matplotlib.pyplot as plt

names = ["A", "B", "C"]
marks = [80, 90, 75]

plt.bar(names, marks)
plt.title("Bar Chart")
plt.show()


#Pie chart

import matplotlib.pyplot as plt

labels = ["Python", "Java", "C++"]
sizes = [40, 35, 25]

plt.pie(sizes, labels=labels, autopct="%1.1f%%")
plt.title("Pie Chart")
plt.show()


#scatter Plot

import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [5, 7, 8, 5, 9]

plt.scatter(x, y)
plt.title("Scatter Plot")
plt.show()


#histogram

import matplotlib.pyplot as plt

data = [10, 20, 20, 30, 30, 30, 40]

plt.hist(data)
plt.title("Histogram")
plt.show()

