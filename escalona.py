#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, re
import networkx as nx

def main():
	schedule = []
	schedule_id = 1
	transaction_set = set() #sets nao permitem repetições
	transactions_to_commit = set() #sets nao permitem repetições

	for line in sys.stdin:
		transact = {}
		line = line.replace('\n', '') #remove \n
		line = ' '.join(re.split("\s+", line, flags=re.UNICODE)) #remove espacos duplicados

		#aqui, cada campo da transacao é obtida ao
		#cortar a string usando o espaço como separador
		transact['timestamp'] = int(line.split(' ')[0])
		transact['id']        = int(line.split(' ')[1])
		transact['operation'] = line.split(' ')[2].upper()
		transact['variable']  = line.split(' ')[3]
		schedule.append(transact.copy())

		transaction_set.add(transact['id']) #lista de transacoes para printar na saida
		transactions_to_commit.add(transact['id']) #lista de transacoes dos commits pendentes

		if transact['operation'] == 'C':
			transactions_to_commit.discard(transact['id'])

		if len(transactions_to_commit) == 0:
			if is_conflict_serializable(schedule[:]):
				conflict_result = 'SS'
			else:
				conflict_result = 'NS'

			if is_view_serializable(schedule[:]):
				view_result = 'SV'
			else:
				view_result = 'NV'

			#trata a string de lista de transacoes para printar na saida
			#"[0,1,2]" => "0,1,2"
			transaction_list = ''.join('{},'.format(t) for t in sorted(transaction_set))[:-1]

			#printa o resultado
			print '{} {} {} {}'.format(schedule_id, transaction_list, conflict_result, view_result)
			
			#zera todas as variaveis
			schedule = []
			schedule_id += 1
			transaction_set.clear()
			transactions_to_commit.clear()

def is_view_serializable(schedule):
	#obter todas as ids
	ids = set([t['id'] for t in schedule])

	#obter todos as variaveis
	variables = set([t['variable'] for t in schedule if t['variable']!='-'])

	#obter todos os timestamps
	timestamps = set([t['timestamp'] for t in schedule])


	#1. A node for each transaction and additional nodes for the hypothetical transactions T0 and  Tf.
	#transacao T0 que escreve em todas as variaveis
	i = -1
	for variable in variables:
		transaction_T0 = {}
		transaction_T0['timestamp'] = i
		transaction_T0['id'] = 0
		transaction_T0['operation'] = 'W'
		transaction_T0['variable'] = variable
		schedule.insert(0, transaction_T0)
		i -= 1


	#transacao Tf que le todas as variaveis
	id_f = len(ids) + 1
	i = len(timestamps) + 1
	for variable in variables:
		transaction_TF = {}
		transaction_TF['timestamp'] = i
		transaction_TF['id'] = id_f
		transaction_TF['operation'] = 'R'
		transaction_TF['variable'] = variable
		schedule.append(transaction_TF)
		i += 1


	#cria um grafo
	schedule_graph = nx.DiGraph()

	#cria um nodo para T do escalonamento S
	for transaction in schedule:
		schedule_graph.add_node(transaction['id'])
	

	possible_pairs = []

	#2. For each action ri(X) with source Tj, place an arc from Tj to Ti.
	for Ti, i in zip(schedule, xrange(0, len(schedule))):
		if Ti['operation'] == 'R':
			previous_schedule = [t for t in schedule[:i]]
			previous_schedule.reverse()

			#search for Tj that is Ti's source
			for Tj in previous_schedule:
				if (Tj['operation'] == 'W' and
						Tj['variable'] == Ti['variable'] and
						Tj['id'] != Ti['id']):
					#add an edge Tj->Ti
					schedule_graph.add_edge(Tj['id'], Ti['id'])
					break

			
			#search for possibles Tk that also writes to X
			Tk_list = []
			for Tk in schedule:
				if (Tk['operation'] == 'W' and
						Tk['variable'] == Ti['variable'] and
						Tk['variable'] == Tj['variable'] and
						Tk['id'] != Ti['id'] and
						Tk['id'] != Tj['id']):
					Tk_list.append(Tk['id'])
			Tk_list = set(Tk_list)


			#adiciona um par de arestas possiveis (antes ou depois de Ti->Tj)
			for Tk in Tk_list:
				#caso especial: se Tj é o nodo inicial T0
				if Tj['id'] == 0:
					schedule_graph.add_edge(Ti['id'], Tk)
				#caso especial: se Ti é o nodo final Tf
				elif Ti['id'] == id_f:
					schedule_graph.add_edge(Tk, Tj['id'])
				#caso default: adiciona numa lista para verificar depois
				else:
					possible_pairs.append([[Tk, Tj['id']], [Ti['id'], Tk]])
					

	#gera uma string binaria para todas as combinações
	#possíveis de Tk's no grafo
	#ex:     "0110" => [antes, depois, depois, antes]
	num_of_possible_pairs = len(possible_pairs)
	for i in xrange(0, num_of_possible_pairs ** 2):
		#gera uma string binaria
		#ex: tamanho da lista de pares: 4, string: "0000"
		test_string = "{:b}".format(i).zfill(len(possible_pairs))

		#cria uma copia do grafo base
		test_graph = schedule_graph.copy()

		#para cada possibilidade na lista
		for possibility, pair in zip(test_string, possible_pairs):
			#adiciona uma das possibilidades ao grafo
			possibility = int(possibility)
			schedule_graph.add_edge(pair[possibility][0], pair[possibility][1])

		#verifica se tem ciclo
		cycles = [cycle for cycle in nx.simple_cycles(test_graph)]
		if len(cycles) == 0:
			return True
			
	#caso não exista nenhum TK
	else:
		#verifica se tem ciclo
		cycles = [cycle for cycle in nx.simple_cycles(schedule_graph)]
		if len(cycles) == 0:
			return True

	return False


def is_conflict_serializable(schedule):
	#cria um grafo
	schedule_graph = nx.DiGraph()

	#cria um nodo para T do escalonamento S
	for transaction in schedule:
		schedule_graph.add_node(transaction['id'])

	#Para cada Tj
	for Tj, j in zip(schedule, xrange(0,len(schedule))):
		#Aresta Ti -> Tj para cada r(x) em Tj depois de w(x) em Ti
		if Tj['operation'] == 'R':
			for Ti in schedule[:j]:
				if Ti['operation'] == 'W' and Ti['variable'] == Tj['variable'] and Ti['id'] != Tj['id']:
					schedule_graph.add_edge(Ti['id'], Tj['id'])

		#Aresta Ti -> Tj para cada w(x) em Tj depois de r(x) em Ti
		if Tj['operation'] == 'W':
			for Ti in schedule[:j]:
				if Ti['operation'] == 'R' and Ti['variable'] == Tj['variable'] and Ti['id'] != Tj['id']:
					schedule_graph.add_edge(Ti['id'], Tj['id'])
					

		#Aresta Ti -> Tj para cada w(x) em Tj depois de w(x) em Ti
		if Tj['operation'] == 'W':
			for Ti in schedule[:j]:
				if Ti['operation'] == 'W' and Ti['variable'] == Tj['variable'] and Ti['id'] != Tj['id']:
					schedule_graph.add_edge(Ti['id'], Tj['id'])


		#Remove todos os nodos de Tj depois de um commit
		elif Tj['operation'] == 'C':
			schedule_graph.remove_node(Tj['id'])


		#verifica se tem ciclo
		cycles = [cycle for cycle in nx.simple_cycles(schedule_graph)]
		if len(cycles) > 0:
			return False

	return True

if __name__ == "__main__":
	main()