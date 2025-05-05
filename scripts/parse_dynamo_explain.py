def find_graph_breaks_line(file_path):
	print("here")
	with open(file_path, 'r') as file:
		for line in file:
			print(line)
			if 'Graph Breaks' in line:
				print("LOOK HERE")
				print(line)
				break

if __name__ == "__main__":
	find_graph_breaks_line('dynamo_explanation.txt')
