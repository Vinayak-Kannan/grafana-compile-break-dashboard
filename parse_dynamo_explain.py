def find_graph_breaks_line(file_path):
	with open(file_path, 'r') as file:
		for line in file:
			if 'Graph Breaks' in line:
				print(line)
				break

if __name__ == "__main__":
	find_graph_breaks_line('dynamo_explanation.txt')
