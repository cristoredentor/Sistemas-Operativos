# -*- coding: utf-8 -*-
"""
Simulación de asignación de memoria principal: arreglo + lista doblemente ligada.

La memoria es un arreglo de celdas con dos tipos de bloque:

    /i  dato  dato  ...  dato  /f        <- bloque ocupado (celdas con el pid)
    ----  ----  ----  ...  ----          <- hueco (solo celdas vacías, sin marcas)

Todo lo que va después de /i pertenece al mismo bloque ocupado hasta llegar a /f.
Un hueco es una racha de celdas vacías; dos huecos nunca quedan contiguos
(se fusionan), porque en el arreglo serían indistinguibles.

Políticas implementadas: First Fit, Next Fit, Best Fit, Worst Fit y Quick Fit.
"""

import random

# ---------------------------------------------------------------------------
# Parámetros de la simulación
# ---------------------------------------------------------------------------
MEMORY_SIZE = 128            #(Cambio, estaba mal hecho el tamaño de la memoria) 256 KB / 2 KB por unidad = 128 unidades (1 celda = 1 unidad de memoria)
START = "/i"                 # marca de inicio de bloque
END = "/f"                   # marca de fin de bloque
EMPTY = None                 # celda vacía
MARKER_CELLS = 0             # el enunciado no cuenta marcas: un proceso de n unidades ocupa n celdas
                             # (/i y /f se siguen escribiendo, pero encima de la primera y última celda del bloque)

MIN_REQUEST = 3              # tamaño mínimo de un dato (unidades)
MAX_REQUEST = 10             # tamaño máximo de un dato (unidades)
MAX_FRAGMENT = 2             # un hueco de 1 o 2 unidades cuenta como fragmento externo
MAX_ACTIVE = 18              # procesos vivos como máximo en el flujo de peticiones (Tiempo de vida: con el máximo alcanzado solo se libera)
ALLOC_PROBABILITY = 0.6      # probabilidad de pedir memoria (si no, se libera) (Tiempo de vida: controla qué tan seguido muere un proceso)
TOTAL_REQUESTS = 10000
SEED = 2026

INITIAL_FILL = 0.7           # fracción de memoria ocupada al generar bloques aleatorios
INITIAL_FREE_PROBABILITY = 0.4   # (Tiempo de vida) probabilidad de que un proceso inicial muera antes de empezar
CONSISTENCY_CHECK_EVERY = 100

MEMORY = []                  #(Añadid por mí) Genere un arreglo real que es el que va a usarse para simular la memoria


# ---------------------------------------------------------------------------
# Lista doblemente ligada
# ---------------------------------------------------------------------------
class Node:
    """
    Un bloque de memoria: hueco u ocupado por un proceso.
    Sigue el formato de las presentaciones, cada nodo tiene su 
    tamaño y la posición en la que empieza.
    """

    def __init__(self, start, weight, is_hole, pid=None):
        self.start = start         # primera celda del bloque en el arreglo (/i si está ocupado)
        self.weight = weight       # celdas que ocupa en el arreglo
        self.is_hole = is_hole
        self.pid = pid
        self.prev = None
        self.next = None

    @property
    def position(self):
        """Primera celda de datos: después de /i en un ocupado, la misma 'start' en un hueco."""
        res = None  # (Modificado por mí) 
        if self.is_hole: 
            res = self.start
        else:
            res = self.start + 1 

        return res


    @property
    def end(self):
        """Última celda del bloque (/f si está ocupado)."""
        return self.start + self.weight - 1


def fits(node, need):
    """Este método verifica si el dato que queremos meter cabe en la memoria"""
    return node.is_hole and node.weight >= need


# ---------------------------------------------------------------------------
# Políticas de asignación
# ---------------------------------------------------------------------------

# Se quitó la clase base AllocationStrategy. La memoria llama directamente
# a los métodos de la política (reset, on_hole_added, etc.) suponiendo que existen.

# ================================================================================
#                              "Políticas vistas en clase"
# ================================================================================


class FirstFit:  
    """Toma el primer hueco en el que cabe el dato."""
    name = "First Fit"
    tracks_cursor = False
    keeps_hole_index = False

    def find_hole(self, memory, need):
        visited = 0
        curr = memory.head
        while curr is not None and not fits(curr, need):  #Al usar fits estás verificando si es hole
            visited += 1
            curr = curr.next
        if curr is not None:  # también cuenta el nodo donde sí cabe, igual que las demás políticas
            visited += 1

        return curr, visited

class NextFit: 
    """Como First Fit, pero empieza a buscar donde se quedó la última asignación."""
    name = "Next Fit"
    tracks_cursor = True
    keeps_hole_index = False

    def reset(self, memory):
        self.pointer = memory.head   # Pointer: nodo donde empieza la siguiente búsqueda

    def find_hole(self, memory, need):
        curr = self.pointer
        visited = 1
        while visited < memory.node_count and not fits(curr, need):
            curr = curr.next if curr.next is not None else memory.head   # da la vuelta
            visited += 1
        return (curr if fits(curr, need) else None), visited

    def after_allocate(self, memory, node):
        self.pointer = node.next if node.next is not None else memory.head

    def on_node_merged(self, memory, removed, survivor):
        # si el nodo al que apuntábamos desapareció al fusionar, apuntamos al que lo absorbió
        if self.pointer is removed:
            self.pointer = survivor


class BestFit:

    """Toma el hueco más pequeño en el que cabe el dato (se detiene si encuentra uno exacto)."""
    name = "Best Fit"
    tracks_cursor = False
    keeps_hole_index = False

    def find_hole(self, memory, need):
        bandera = False  #(Modificado por mí) Añadimos una bandera para que acabe en vez de la condición rara que usaba Claude
        best = None
        visited = 0
        curr = memory.head

        while curr is not None and not bandera: 
            visited += 1
            if fits(curr, need):
                best = curr
                if(best.weight == need):  # Si son iguales la bandera es true y se acaba el while en la sig iteración
                    bandera = True 
            curr = curr.next

        return best, visited


class WorstFit:
    """Toma el hueco más grande."""
    name = "Worst Fit"
    tracks_cursor = False
    keeps_hole_index = False

    def find_hole(self, memory, need):
        largest = None
        visited = 0
        curr = memory.head
        while curr is not None: #Visita todos los nodos
            visited += 1
            if curr.is_hole and (largest is None or curr.weight > largest.weight): #Si es el primero o el de mayor tamaño 
                largest = curr                   #actualizamos el valor del más grande
            curr = curr.next
        return (largest if largest is not None and fits(largest, need) else None), visited #Regresa el nodo mas grande y los visitados




"""
(OBSERVACIÓN): 
Me dí cuenta de que Claude había hecho una clase de Quick Fit que 
no concuerda con la definición que vimos en clase:

 Keep lists of holes of different sizes Poor coalescing performance.
"""

#Método hecho por mí en vista de que no QuickFit no era estrictamente  lo que vimos

"""
Método QuickFit que tiene un diccionario buckets con los huecos y dentro otro 
diccionario con la posición del hueco referenciando al nodo, 
"""
class QuickFit: #(Modificado por mí)

    name = "Quick Fit"
    tracks_cursor = False  
    keeps_hole_index = True 

    def __init__(self):  
        self.buckets = {}     # Tiene más sentido añadir el diccionario con los hoyos al declarar la clase

    def reset(self, memory):
        self.buckets = {}
        for node in memory.nodes():
            if node.is_hole:
                self.on_hole_added(memory, node)

    def find_hole(self, memory, need):
        found = None
        visited = 0
        size = need
        while found is None and size <= memory.size:  # Primero el tamaño exacto, luego los mayores
            if size in self.buckets:
                found = next(iter(self.buckets[size].values()))  # Al asignar found acaba el while
                visited += 1
            size += 1
        return found, visited

    def on_hole_added(self, memory, node):
        if node.weight not in self.buckets:  # Si no hay huecos de ese tamaño se crea la entrada
            self.buckets[node.weight] = {}   # creamos un diccionario dentro del diccionario con el formato {tamaño: {posición: nodo}}
        self.buckets[node.weight][node.position] = node

    def on_hole_removed(self, memory, node):
        del self.buckets[node.weight][node.position]
        if not self.buckets[node.weight]:  # Si ya no hay huecos de ese tamaño se borra la entrada
            del self.buckets[node.weight]


# ---------------------------------------------------------------------------
# Memoria: arreglo de celdas + lista doblemente ligada de bloques
# ---------------------------------------------------------------------------
class Memory:

    #(Modificado por mí) inicializamos la memoria como un arreglo vacio

    def _reset_to_single_hole(self):
        """Reinicia la instancia con un único hueco y con el arreglo global MEMORY como respaldo real."""
        global MEMORY
        MEMORY = [EMPTY] * self.size
        self.cells = MEMORY
        self.head = Node(start=0, weight=self.size, is_hole=True)
        self.node_count = 1
        self.busy = {}                 # pid -> nodo
        if self.strategy.tracks_cursor or self.strategy.keeps_hole_index:
            self.strategy.reset(self)

    def __init__(self, size=MEMORY_SIZE, strategy=None): # Por default la estrategia es Nula
        self.size = size
        self.strategy = strategy if strategy is not None else FirstFit() # Si no se especifica estrategia se usa first fit
        self._reset_to_single_hole()

    # --- recorridos -------------------------------------------------------
    
    def nodes(self):      #Regresamos el último nodo que no sea nulo
        curr = self.head
        while curr is not None:
            yield curr
            curr = curr.next     

    def holes(self):
        return [node for node in self.nodes() if node.is_hole]  #Así obtenemos todos los nodos que son hoyos

    def used_cells(self):   
        return sum(node.weight for node in self.busy.values())    #SUmamos todos los pesos de los nodos para tener los espacios ocuapdos

    # --- operaciones sobre el arreglo y la lista --------------------------
    def _link_after(self, node, new):
        new.prev = node
        new.next = node.next
        if node.next is not None:
            node.next.prev = new
        node.next = new
        self.node_count += 1

    def _unlink(self, node):
        node.prev.next = node.next
        if node.next is not None:
            node.next.prev = node.prev
        self.node_count -= 1

    def place(self, hole, pid, size):
        """
        Escribe /i, el dato de 'size' celdas y /f al inicio de 'hole'.
        Si sobran celdas, se quedan como un hueco nuevo justo después.
        """
        need = size + MARKER_CELLS
        remainder = hole.weight - need
        if self.strategy.keeps_hole_index:
            self.strategy.on_hole_removed(self, hole)
        if remainder > 0:
            rest = Node(start=hole.start + need, weight=remainder, is_hole=True)
            self._link_after(hole, rest)
            hole.weight = need
            if self.strategy.keeps_hole_index:
                self.strategy.on_hole_added(self, rest)
        hole.is_hole = False
        hole.pid = pid
        self.cells[hole.start] = START
        for i in range(hole.position, hole.end):
            self.cells[i] = pid
        self.cells[hole.end] = END
        self.busy[pid] = hole
        return hole

    def allocate(self, pid, size):
        """Busca un hueco con la política actual y coloca el dato. Devuelve (nodo o None, visitados)."""
        hole, visited = self.strategy.find_hole(self, size + MARKER_CELLS)
        node = None
        if hole is not None:
            node = self.place(hole, pid, size)
            if self.strategy.tracks_cursor:
                self.strategy.after_allocate(self, node)
        return node, visited

    def free(self, pid):
        """Libera el bloque de 'pid' y lo fusiona con los huecos vecinos."""
        node = self.busy.pop(pid)
        for i in range(node.start, node.end + 1):   # se borran también /i y /f
            self.cells[i] = EMPTY
        node.is_hole = True
        node.pid = None
        survivor = node
        if node.prev is not None and node.prev.is_hole:
            if self.strategy.keeps_hole_index:
                self.strategy.on_hole_removed(self, node.prev)
            survivor = self._merge(node.prev, node)
        if survivor.next is not None and survivor.next.is_hole:
            if self.strategy.keeps_hole_index:
                self.strategy.on_hole_removed(self, survivor.next)
            survivor = self._merge(survivor, survivor.next)
        if self.strategy.keeps_hole_index:
            self.strategy.on_hole_added(self, survivor)
        return survivor

    # --- interfaz del componente de Memoria  -----
    def allocate_mem(self, process_id, num_units):
        """Asigna num_units unidades a process_id. Devuelve los nodos recorridos o -1 si no hay hueco."""
        node, visited = self.allocate(process_id, num_units)
        return visited if node is not None else -1

    def deallocate_mem(self, process_id):
        """Libera la memoria de process_id. Devuelve 1 si tenía memoria asignada, -1 si no."""
        if process_id not in self.busy:
            return -1
        self.free(process_id)
        return 1

    def fragment_count(self):
        """Número de huecos de 1 o 2 unidades."""
        return sum(1 for hole in self.holes() if hole.weight <= MAX_FRAGMENT)

    def _merge(self, left, right):
        """Fusiona dos huecos contiguos. En el arreglo ya son una sola racha vacía; solo cambia la lista."""
        left.weight += right.weight
        self._unlink(right)
        if self.strategy.tracks_cursor:
            self.strategy.on_node_merged(self, right, left)
        return left

    def _first_hole_that_fits(self, need):
        curr = self.head
        while curr is not None and not fits(curr, need):
            curr = curr.next
        return curr

    # --- lectura del arreglo celda por celda -----------------------------
    def _skip_block(self, i):
        """Lee celda por celda el bloque que empieza en 'i' y devuelve el índice del siguiente."""
        if self.cells[i] == START:
            while self.cells[i] != END:
                i += 1
            i += 1                # leer /f
        else:
            while i < self.size and self.cells[i] is EMPTY:
                i += 1
        return i

    # --- verificación ------------------------------------------------------
    def parse_blocks_from_array(self):
        """Reconstruye los bloques leyendo solo el arreglo: [(position, weight, is_hole, pid)]."""
        blocks = []
        i = 0
        while i < self.size:
            start = i
            i = self._skip_block(i)
            if self.cells[start] is EMPTY:
                blocks.append((start, i - start, True, None))
            else:
                blocks.append((start + 1, i - start, False, self.cells[start + 1]))
        return blocks

    def verify_consistency(self):
        """Comprueba que la lista doblemente ligada describe exactamente lo que hay en el arreglo."""
        from_list = [(n.position, n.weight, n.is_hole, n.pid) for n in self.nodes()]
        from_array = self.parse_blocks_from_array()
        if from_list != from_array:
            raise AssertionError(f"Lista y arreglo no coinciden:\n lista:   {from_list}\n arreglo: {from_array}")
        if len(from_list) != self.node_count:
            raise AssertionError(f"node_count={self.node_count} pero la lista tiene {len(from_list)} nodos")
        backwards = 0
        tail = self.head
        while tail.next is not None:
            tail = tail.next
        while tail is not None:
            backwards += 1
            tail = tail.prev
        if backwards != self.node_count:
            raise AssertionError("Los enlaces prev no coinciden con los enlaces next")


# (Modificado por mí) No me hacía sentido que assign_random_busy_spaces dependiera de la clase memoria
def assign_random_busy_spaces(memoria, rng, fill_ratio=INITIAL_FILL,
                              free_probability=INITIAL_FREE_PROBABILITY, first_pid=1):
    """
    Crea bloques ocupados aleatorios: llena la memoria hasta 'fill_ratio' con datos de
    tamaño aleatorio y luego libera algunos al azar para dejar huecos dispersos.
    Usa las mismas operaciones place/free, así arreglo y lista quedan sincronizados.
    Devuelve el siguiente pid disponible.
    """
    pid = first_pid
    placed = True
    while placed and memoria.used_cells() < fill_ratio * memoria.size:
        size = rng.randint(MIN_REQUEST, MAX_REQUEST)
        hole = memoria._first_hole_that_fits(size + MARKER_CELLS)
        placed = hole is not None
        if placed:
            memoria.place(hole, pid, size)
            pid += 1
    for victim in list(memoria.busy):  # (Tiempo de vida) algunos procesos iniciales mueren al azar
        if rng.random() < free_probability:
            memoria.free(victim)
    if memoria.strategy.tracks_cursor or memoria.strategy.keeps_hole_index:
        memoria.strategy.reset(memoria)
    return pid


def generate_request_stream(rng, active_pids, next_pid, count):
    """Secuencia de ('ALLOC', pid, tamaño) y ('FREE', pid, None) a partir de los procesos iniciales."""
    requests = []
    active = list(active_pids)
    for _ in range(count):
        if not active or (len(active) < MAX_ACTIVE and rng.random() < ALLOC_PROBABILITY):
            requests.append(("ALLOC", next_pid, rng.randint(MIN_REQUEST, MAX_REQUEST)))  # (Tiempo de vida) aquí nace el proceso
            active.append(next_pid)
            next_pid += 1
        else:
            pid = rng.choice(active)  # (Tiempo de vida) se elige al azar qué proceso vivo muere
            requests.append(("FREE", pid, None))
            active.remove(pid)
    return requests


def build_scenario(strategy):
    """Misma semilla -> misma memoria inicial y mismo flujo de peticiones para todas las políticas."""
    rng = random.Random(SEED)
    memory = Memory(strategy=strategy)
    next_pid = assign_random_busy_spaces(memory, rng)
    requests = generate_request_stream(rng, memory.busy.keys(), next_pid, TOTAL_REQUESTS)
    return memory, requests


# ---------------------------------------------------------------------------
# Simulación: todas las técnicas reciben cada solicitud a la vez
# ---------------------------------------------------------------------------
class Stats:

    def __init__(self, name):
        self.name = name
        self.alloc_requests = 0
        self.denied = 0
        self.nodes_visited = 0
        self.steps = 0
        self.fragments_sum = 0

    def record_allocation(self, result):
        self.alloc_requests += 1
        if result == -1:
            self.denied += 1
        else:
            self.nodes_visited += result

    def record_step(self, memory):
        self.steps += 1
        self.fragments_sum += memory.fragment_count()


def average(total, count):
    return total / count if count else 0.0


def run_simulation():
    """Genera las solicitudes y, para cada una, invoca la función correspondiente en cada técnica."""
    memories = []
    for strategy in [FirstFit(), NextFit(), BestFit(), WorstFit(), QuickFit()]:
        memory, requests = build_scenario(strategy)   # misma semilla -> misma memoria inicial y mismas solicitudes
        memories.append((memory, Stats(strategy.name)))

    for step, (kind, pid, size) in enumerate(requests, start=1):
        for memory, stats in memories:
            if kind == "ALLOC":
                stats.record_allocation(memory.allocate_mem(pid, size))
            else:
                memory.deallocate_mem(pid)
            stats.record_step(memory)   # después de cada solicitud se actualizan los parámetros
            if step % CONSISTENCY_CHECK_EVERY == 0:
                memory.verify_consistency()

    print(f"{TOTAL_REQUESTS} solicitudes, memoria de {MEMORY_SIZE} unidades, procesos de {MIN_REQUEST}-{MAX_REQUEST} unidades")
    print(f"{'Técnica':<10} │ {'Fragmentos':>10} │ {'Nodos recorridos':>16} │ {'Denegadas':>9}")
    for _, s in memories:
        print(f"{s.name:<10} │ {average(s.fragments_sum, s.steps):>10.2f} │ "
              f"{average(s.nodes_visited, s.alloc_requests - s.denied):>16.2f} │ "
              f"{average(s.denied, s.alloc_requests) * 100:>8.2f}%")
    print(f"(promedios por solicitud; fragmento = hueco de 1 a {MAX_FRAGMENT} unidades)")


run_simulation()
