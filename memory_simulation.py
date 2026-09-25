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
import sys
import textwrap
import time

# ---------------------------------------------------------------------------
# Parámetros de la simulación
# ---------------------------------------------------------------------------
MEMORY_SIZE = 256            # celdas de la memoria (1 celda = 1 unidad de memoria)
START = "/i"                 # marca de inicio de bloque
END = "/f"                   # marca de fin de bloque
EMPTY = None                 # celda vacía
MARKER_CELLS = 2             # cada bloque ocupado gasta 2 celdas en /i y /f

MIN_REQUEST = 4              # tamaño mínimo de un dato (celdas)
MAX_REQUEST = 16             # tamaño máximo de un dato (celdas)
MAX_ACTIVE = 18              # procesos vivos como máximo en el flujo de peticiones (Tiempo de vida: con el máximo alcanzado solo se libera)
ALLOC_PROBABILITY = 0.6      # probabilidad de pedir memoria (si no, se libera) (Tiempo de vida: controla qué tan seguido muere un proceso)
TOTAL_REQUESTS = 10000
SEED = 2026

INITIAL_FILL = 0.7           # fracción de memoria ocupada al generar bloques aleatorios
INITIAL_FREE_PROBABILITY = 0.4   # (Tiempo de vida) probabilidad de que un proceso inicial muera antes de empezar
CONSISTENCY_CHECK_EVERY = 100

ROW_WIDTH = 64               # celdas por renglón al dibujar la memoria
USE_COLORS = sys.stdout.isatty()
SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


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

    def __repr__(self):
        label = "hueco" if self.is_hole else f"P{self.pid}"
        return f"[{label} pos={self.position} w={self.weight}]"


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
    tracks_cursor = False  # (modificado por Claude) usa after_allocate y on_node_merged
    keeps_hole_index = False  # (modificado por Claude) usa on_hole_added y on_hole_removed

    def __init__(self):  # (modificado por Claude)
        self.maintenance_visits = 0  # (modificado por Claude)

    def find_hole(self, memory, need):
        visited = 0
        curr = memory.head
        while curr is not None and not fits(curr, need):  #Al usar fits estás verificando si es hole
            visited += 1
            curr = curr.next

        return curr, visited

class NextFit: 
    """Como First Fit, pero empieza a buscar donde se quedó la última asignación."""
    name = "Next Fit"
    tracks_cursor = True  # (modificado por Claude) usa after_allocate y on_node_merged
    keeps_hole_index = False  # (modificado por Claude) usa on_hole_added y on_hole_removed

    def __init__(self):  # (modificado por Claude)
        self.maintenance_visits = 0  # (modificado por Claude)

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


class BestFit:  # (modificado por Claude)

    """Toma el hueco más pequeño en el que cabe el dato (se detiene si encuentra uno exacto)."""
    name = "Best Fit"
    tracks_cursor = False  # (modificado por Claude) usa after_allocate y on_node_merged
    keeps_hole_index = False  # (modificado por Claude) usa on_hole_added y on_hole_removed

    def __init__(self):  # (modificado por Claude)
        self.maintenance_visits = 0  # (modificado por Claude)

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


class WorstFit:  # (modificado por Claude)
    """Toma el hueco más grande."""
    name = "Worst Fit"
    tracks_cursor = False  # (modificado por Claude) usa after_allocate y on_node_merged
    keeps_hole_index = False  # (modificado por Claude) usa on_hole_added y on_hole_removed

    def __init__(self):  # (modificado por Claude)
        self.maintenance_visits = 0  # (modificado por Claude)

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
        self.maintenance_visits = 0  
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
        self.maintenance_visits += 1  # Se saca directo por su posición, sin recorrer
        del self.buckets[node.weight][node.position]
        if not self.buckets[node.weight]:  # Si ya no hay huecos de ese tamaño se borra la entrada
            del self.buckets[node.weight]


"""
(modificado por Claude) Antes se usaba call_if_exists(política, "método", ...), que con hasattr
revisaba en tiempo de ejecución si la política tenía el método y, si no, no hacía nada.
Ahora cada política declara dos banderas de clase y Memory llama directo al método
solo si la bandera correspondiente está prendida:
  - tracks_cursor:    la política guarda un puntero (Next Fit), así que necesita
                      reset, after_allocate y on_node_merged.
  - keeps_hole_index: la política guarda su propio registro de huecos (Quick Fit),
                      así que necesita reset, on_hole_added y on_hole_removed.
Si se agrega una política nueva basta con ponerle sus banderas; Memory no cambia.
"""
# ---------------------------------------------------------------------------
# Memoria: arreglo de celdas + lista doblemente ligada de bloques
# ---------------------------------------------------------------------------
class Memory:

    def __init__(self, size=MEMORY_SIZE, strategy=None): # Por default la estrategia es Nula
        self.size = size
        self.strategy = strategy if strategy is not None else FirstFit() # Si no se especifica estrategia se usa first fit
        self._reset_to_single_hole()

    def _reset_to_single_hole(self):
        """Estado inicial: un único hueco del tamaño de toda la memoria (position=0, sin marcas)."""
        self.cells = [EMPTY] * self.size
        self.head = Node(start=0, weight=self.size, is_hole=True)
        self.node_count = 1
        self.busy = {}                 # pid -> nodo
        if self.strategy.tracks_cursor or self.strategy.keeps_hole_index:  # (modificado por Claude) Solo llama a estos métodos si la bandera lo permite
            self.strategy.reset(self)  # (modificado por Claude)

    # --- recorridos -------------------------------------------------------
    def nodes(self):
        curr = self.head
        while curr is not None:
            yield curr
            curr = curr.next

    def holes(self):
        return [node for node in self.nodes() if node.is_hole]  #Así obtenemos todos los nodos que son hoyos

    def used_cells(self):
        return sum(node.weight for node in self.busy.values())

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
        if self.strategy.keeps_hole_index:  # (modificado por Claude)
            self.strategy.on_hole_removed(self, hole)  # (modificado por Claude)
        if remainder > 0:
            rest = Node(start=hole.start + need, weight=remainder, is_hole=True)
            self._link_after(hole, rest)
            hole.weight = need
            if self.strategy.keeps_hole_index:  # (modificado por Claude)
                self.strategy.on_hole_added(self, rest)  # (modificado por Claude)
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
            if self.strategy.tracks_cursor:  # (modificado por Claude)
                self.strategy.after_allocate(self, node)  # (modificado por Claude)
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
            if self.strategy.keeps_hole_index:  # (modificado por Claude)
                self.strategy.on_hole_removed(self, node.prev)  # (modificado por Claude)
            survivor = self._merge(node.prev, node)
        if survivor.next is not None and survivor.next.is_hole:
            if self.strategy.keeps_hole_index:  # (modificado por Claude)
                self.strategy.on_hole_removed(self, survivor.next)  # (modificado por Claude)
            survivor = self._merge(survivor, survivor.next)
        if self.strategy.keeps_hole_index:  # (modificado por Claude)
            self.strategy.on_hole_added(self, survivor)  # (modificado por Claude)
        return survivor

    def _merge(self, left, right):
        """Fusiona dos huecos contiguos. En el arreglo ya son una sola racha vacía; solo cambia la lista."""
        left.weight += right.weight
        self._unlink(right)
        if self.strategy.tracks_cursor:  # (modificado por Claude)
            self.strategy.on_node_merged(self, right, left)  # (modificado por Claude)
        return left

    # --- generación de bloques aleatorios ---------------------------------
    def assign_random_busy_spaces(self, rng, fill_ratio=INITIAL_FILL,
                                  free_probability=INITIAL_FREE_PROBABILITY, first_pid=1):
        """
        Crea bloques ocupados aleatorios: llena la memoria hasta 'fill_ratio' con datos de
        tamaño aleatorio y luego libera algunos al azar para dejar huecos dispersos.
        Usa las mismas operaciones place/free, así arreglo y lista quedan sincronizados.
        Devuelve el siguiente pid disponible.
        """
        self._reset_to_single_hole()
        pid = first_pid
        placed = True
        while placed and self.used_cells() < fill_ratio * self.size:
            size = rng.randint(MIN_REQUEST, MAX_REQUEST)
            hole = self._first_hole_that_fits(size + MARKER_CELLS)
            placed = hole is not None
            if placed:
                self.place(hole, pid, size)
                pid += 1
        for victim in list(self.busy):  # (Tiempo de vida) algunos procesos iniciales mueren al azar
            if rng.random() < free_probability:
                self.free(victim)
        if self.strategy.tracks_cursor or self.strategy.keeps_hole_index:  # (modificado por Claude)
            self.strategy.reset(self)  # (modificado por Claude)
        return pid

    def _first_hole_that_fits(self, need):
        curr = self.head
        while curr is not None and not fits(curr, need):
            curr = curr.next
        return curr

    # --- búsqueda sin lista: recorrer el arreglo celda por celda ------------
    def find_first_fit_by_array_scan(self, need):
        """
        First Fit leyendo solo el arreglo. Hay que leer cada celda: las vacías para
        medir el hueco y las de un bloque ocupado para llegar a su /f.
        Devuelve (índice de inicio del hueco o None, celdas leídas).
        """
        i = 0
        found = None
        while found is None and i < self.size:
            start = i
            i = self._skip_block(i)
            if self.cells[start] is EMPTY and i - start >= need:
                found = start
        return found, i

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


    # -------------------------------------------------------------------------------
    #                  Método para visualización de resultados
    #--------------------------------------------------------------------------------


    def _cell_char(self, cell):
        if cell == START:
            return paint("[", 90)
        if cell == END:
            return paint("]", 90)
        if cell is EMPTY:
            return paint("·", 90)
        return paint(SYMBOLS[(cell - 1) % len(SYMBOLS)], 31 + cell % 6)

    def render(self):
        chars = [self._cell_char(cell) for cell in self.cells]
        rows = []
        for offset in range(0, self.size, ROW_WIDTH):
            rows.append(f"  {offset:>4} │ " + "".join(chars[offset:offset + ROW_WIDTH]))
        return "\n".join(rows)

    def render_list(self, width=100):
        text = " ⇄ ".join(repr(node) for node in self.nodes())
        return textwrap.fill(text, width=width, initial_indent="  ", subsequent_indent="  ")

    def show(self, title):
        print(f"\n{title}")
        print(self.render())
        print(self.render_list())


#Este sólo es un metodo para que se vean bonitos los resultados, no afecta el resultado de la tarea

def paint(text, color):
    return f"\033[{color}m{text}\033[0m" if USE_COLORS else text



# ---------------------------------------------------------------------------
# Demostración paso a paso
# ---------------------------------------------------------------------------
def demo():
    print("=" * 100)
    print("DEMOSTRACIÓN (memoria de 64 celdas, First Fit)")
    print("Leyenda: [ = /i   ] = /f   · = celda vacía (hueco)   letra = dato del proceso (A = P1, B = P2, ...)")
    print("=" * 100)
    memory = Memory(size=64, strategy=FirstFit())
    memory.show("Estado inicial: un solo hueco que ocupa toda la memoria")

    for pid, size in [(1, 10), (2, 6), (3, 12)]:
        node, visited = memory.allocate(pid, size)
        memory.show(f"P{pid} pide {size} celdas (+2 de /i y /f) -> {node}, nodos visitados: {visited}")

    memory.free(2)
    memory.show("Se libera P2: queda un hueco entre P1 y P3")

    node, visited = memory.allocate(4, 5)
    memory.show(f"P4 pide 5 celdas y ocupa 7 de las 8 del hueco: queda un hueco de 1 celda "
                f"donde ya no cabe nada (fragmentación externa) -> {node}, nodos visitados: {visited}")

    memory.free(3)
    memory.show("Se libera P3: su bloque se fusiona con el hueco final")
    memory.free(1)
    memory.free(4)
    memory.show("Se liberan P1 y P4: los huecos contiguos se fusionan y todo vuelve a ser un solo hueco")
    memory.verify_consistency()


# ---------------------------------------------------------------------------
# Simulación de las cinco políticas
# ---------------------------------------------------------------------------
class Stats:

    def __init__(self, name):
        self.name = name
        self.alloc_requests = 0
        self.denied = 0
        self.nodes_visited = 0
        self.cells_scanned = 0
        self.list_seconds = 0.0
        self.array_seconds = 0.0
        self.alloc_maintenance = 0
        self.frees = 0
        self.free_maintenance = 0
        self.steps = 0
        self.holes_sum = 0
        self.external_fragments_sum = 0
        self.fragmented_cells_sum = 0

    def record_step(self, memory):
        holes = memory.holes()
        self.steps += 1
        self.holes_sum += len(holes)
        # hueco inútil: ni el dato más pequeño (con su /i y /f) cabe en él
        useless = [h for h in holes if not fits(h, MIN_REQUEST + MARKER_CELLS)]
        self.external_fragments_sum += len(useless)
        self.fragmented_cells_sum += sum(h.weight for h in useless)


def average(total, count):
    return total / count if count else 0.0


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
    next_pid = memory.assign_random_busy_spaces(rng)
    requests = generate_request_stream(rng, memory.busy.keys(), next_pid, TOTAL_REQUESTS)
    return memory, requests


def run_strategy(strategy):
    memory, requests = build_scenario(strategy)
    stats = Stats(strategy.name)

    for step, (kind, pid, size) in enumerate(requests, start=1):
        if kind == "ALLOC":
            need = size + MARKER_CELLS
            stats.alloc_requests += 1

            t0 = time.perf_counter()
            _, cells = memory.find_first_fit_by_array_scan(need)
            stats.array_seconds += time.perf_counter() - t0
            stats.cells_scanned += cells

            maintenance_before = strategy.maintenance_visits
            t0 = time.perf_counter()
            hole, visited = strategy.find_hole(memory, need)
            stats.list_seconds += time.perf_counter() - t0
            stats.nodes_visited += visited

            if hole is None:
                stats.denied += 1
            else:
                node = memory.place(hole, pid, size)
                if strategy.tracks_cursor:  # (modificado por Claude)
                    strategy.after_allocate(memory, node)  # (modificado por Claude)
            stats.alloc_maintenance += strategy.maintenance_visits - maintenance_before

        elif pid in memory.busy:   # si su asignación fue rechazada, no hay nada que liberar
            maintenance_before = strategy.maintenance_visits
            memory.free(pid)
            stats.frees += 1
            stats.free_maintenance += strategy.maintenance_visits - maintenance_before

        stats.record_step(memory)
        if step % CONSISTENCY_CHECK_EVERY == 0:
            memory.verify_consistency()

    memory.verify_consistency()
    return memory, stats


def print_results(results):
    print("\n" + "=" * 100)
    print(f"RESULTADOS: {TOTAL_REQUESTS} peticiones, memoria de {MEMORY_SIZE} celdas, "
          f"datos de {MIN_REQUEST}-{MAX_REQUEST} celdas")
    print("=" * 100)

    print("\nBúsqueda de hueco: lista doblemente ligada vs recorrer el arreglo")
    print(f"  {'Política':<11} │ {'Nodos visit.':>12} │ {'Celdas arreglo*':>15} │ {'Menos lecturas':>14} │ "
          f"{'µs lista':>8} │ {'µs arreglo':>10}")
    for _, s in results:
        nodes = average(s.nodes_visited, s.alloc_requests)
        cells = average(s.cells_scanned, s.alloc_requests)
        print(f"  {s.name:<11} │ {nodes:>12.2f} │ {cells:>15.2f} │ {average(cells, nodes):>13.1f}x │ "
              f"{average(s.list_seconds, s.alloc_requests) * 1e6:>8.2f} │ "
              f"{average(s.array_seconds, s.alloc_requests) * 1e6:>10.2f}")
    print("  * First Fit leyendo celda por celda sobre la misma memoria en ese instante.")

    print("\nCalidad de la asignación (promedios por paso)")
    print(f"  {'Política':<11} │ {'Denegadas':>9} │ {'Huecos':>7} │ {'Frag. externa**':>15} │ "
          f"{'Celdas en frag.':>15} │ {'Mant./asignar':>13} │ {'Mant./liberar':>13}")
    for _, s in results:
        print(f"  {s.name:<11} │ {average(s.denied, s.alloc_requests) * 100:>8.2f}% │ "
              f"{average(s.holes_sum, s.steps):>7.2f} │ {average(s.external_fragments_sum, s.steps):>15.2f} │ "
              f"{average(s.fragmented_cells_sum, s.steps):>15.2f} │ "
              f"{average(s.alloc_maintenance, s.alloc_requests):>13.2f} │ "
              f"{average(s.free_maintenance, s.frees):>13.2f}")
    print(f"  ** huecos donde ya no cabe ni el dato más pequeño ({MIN_REQUEST} celdas + /i y /f).")
    print("  Mant. = nodos visitados para mantener estructuras auxiliares (las listas por tamaño de Quick Fit).")


def run_simulation():
    strategies = [FirstFit(), NextFit(), BestFit(), WorstFit(), QuickFit()]

    initial_memory, _ = build_scenario(FirstFit())
    print("\n" + "=" * 100)
    print("SIMULACIÓN")
    print("=" * 100)
    initial_memory.show(f"Memoria inicial generada con assign_random_busy_spaces "
                        f"({initial_memory.node_count} bloques, igual para todas las políticas)")

    results = [run_strategy(strategy) for strategy in strategies]
    print_results(results)

    for memory, stats in results:
        memory.show(f"Memoria final con {stats.name} ({len(memory.holes())} huecos)")


demo()
run_simulation()

