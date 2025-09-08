from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
from functools import reduce, wraps
import json
import os
from datetime import datetime
from dataclasses import dataclass


# ==============================
# Decoradores
# ==============================
def validar_entrada(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for arg in args[1:]:  # Omitir self
            if isinstance(arg, str) and not arg.strip():
                raise ValueError("Los campos de texto no pueden estar vacíos")
            if isinstance(arg, (int, float)) and arg < 0:
                raise ValueError("Los valores numéricos no pueden ser negativos")
        return func(*args, **kwargs)
    return wrapper


def log_operacion(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Ejecutando operación: {func.__name__}")
        resultado = func(*args, **kwargs)
        print(f"Operación {func.__name__} completada exitosamente")
        return resultado
    return wrapper


# ==============================
# Repositorios
# ==============================
class IRepositorio(Protocol):
    def crear(self, entidad: Any) -> bool: ...
    def obtener(self, id: str) -> Optional[Any]: ...
    def listar(self) -> List[Any]: ...
    def actualizar(self, id: str, entidad: Any) -> bool: ...
    def eliminar(self, id: str) -> bool: ...


class RepositorioBase(ABC):
    def __init__(self, archivo: str):
        self.archivo = archivo
    
    @abstractmethod
    def _serializar(self, entidad: Any) -> Dict[str, Any]: ...
    
    @abstractmethod
    def _deserializar(self, data: Dict[str, Any]) -> Any: ...
    
    def _cargar_datos(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.archivo):
            return []
        with open(self.archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _guardar_datos(self, datos: List[Dict[str, Any]]) -> None:
        with open(self.archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)


# ==============================
# Modelos
# ==============================
@dataclass
class Empleado:
    cedula: str
    nombre: str
    sueldo: float
    departamento: str
    cargo: str
    
    @validar_entrada
    def __init__(self, cedula: str, nombre: str, sueldo: float, departamento: str, cargo: str):
        self.cedula = cedula
        self.nombre = nombre
        self.sueldo = sueldo
        self.departamento = departamento
        self.cargo = cargo


class DetalleNomina:
    def __init__(self, id: int, empleado: Empleado, sueldo: float, bono: float, prestamo: float):
        self.id = id
        self.empleado = empleado
        self.sueldo = sueldo
        self.bono = bono
        self.tot_ing = sueldo + bono
        self.iess = round(sueldo * 0.0945, 2)
        self.prestamo = prestamo
        self.tot_des = self.iess + prestamo
        self.neto = self.tot_ing - self.tot_des


class Nomina:
    BONO = 50.0
    PRESTAMO = 20.0
    
    def __init__(self, id: int, aniomes: str):
        self.id = id
        self.aniomes = aniomes
        self.tot_ing = 0.0
        self.tot_des = 0.0
        self.neto = 0.0
        self.detalles: List[DetalleNomina] = []
    
    class Resumen:
        def __init__(self, nomina: 'Nomina'):
            self.nomina = nomina
        
        def generar_estadisticas(self) -> Dict[str, Any]:
            if not self.nomina.detalles:
                return {"total_empleados": 0, "promedio_sueldo": 0, "total_neto": 0}
            
            netos = list(map(lambda d: d.neto, self.nomina.detalles))
            sueldos = list(map(lambda d: d.sueldo, self.nomina.detalles))
            
            total_neto = reduce(lambda a, b: a + b, netos, 0)
            promedio_sueldo = reduce(lambda a, b: a + b, sueldos, 0) / len(sueldos)
            
            empleados_alto_sueldo = list(filter(lambda d: d.sueldo > 1000, self.nomina.detalles))
            mayor_neto = max(self.nomina.detalles, key=lambda d: d.neto)
            menor_neto = min(self.nomina.detalles, key=lambda d: d.neto)
            
            return {
                "total_empleados": len(self.nomina.detalles),
                "total_neto_pagado": total_neto,
                "promedio_sueldos": round(promedio_sueldo, 2),
                "empleados_alto_sueldo": len(empleados_alto_sueldo),
                "empleado_mayor_neto": mayor_neto.empleado.nombre,
                "empleado_menor_neto": menor_neto.empleado.nombre,
                "valor_mayor_neto": mayor_neto.neto,
                "valor_menor_neto": menor_neto.neto
            }
    
    def calcular_totales(self):
        self.tot_ing = sum([d.tot_ing for d in self.detalles])
        self.tot_des = sum([d.tot_des for d in self.detalles])
        self.neto = self.tot_ing - self.tot_des
    
    def obtener_resumen(self) -> 'Nomina.Resumen':
        return self.Resumen(self)


# ==============================
# Repositorio Empleados
# ==============================
class RepositorioEmpleados(RepositorioBase):
    def __init__(self, archivo: str = "empleados.json"):
        super().__init__(archivo)
    
    def _serializar(self, empleado: Empleado) -> Dict[str, Any]:
        return empleado.__dict__
    
    def _deserializar(self, data: Dict[str, Any]) -> Empleado:
        return Empleado(**data)
    
    @log_operacion
    def crear(self, empleado: Empleado) -> bool:
        datos = self._cargar_datos()
        if any(emp["cedula"] == empleado.cedula for emp in datos):
            raise ValueError(f"Ya existe un empleado con cédula {empleado.cedula}")
        datos.append(self._serializar(empleado))
        self._guardar_datos(datos)
        return True
    
    def obtener(self, cedula: str) -> Optional[Empleado]:
        datos = self._cargar_datos()
        emp = next((e for e in datos if e["cedula"] == cedula), None)
        return self._deserializar(emp) if emp else None
    
    def listar(self) -> List[Empleado]:
        return [self._deserializar(emp) for emp in self._cargar_datos()]
    
    @log_operacion
    def actualizar(self, cedula: str, empleado: Empleado) -> bool:
        datos = self._cargar_datos()
        for i, emp in enumerate(datos):
            if emp["cedula"] == cedula:
                datos[i] = self._serializar(empleado)
                self._guardar_datos(datos)
                return True
        return False
    
    @log_operacion
    def eliminar(self, cedula: str) -> bool:
        datos = self._cargar_datos()
        filtrados = [emp for emp in datos if emp["cedula"] != cedula]
        if len(filtrados) < len(datos):
            self._guardar_datos(filtrados)
            return True
        return False


# ==============================
# Servicios
# ==============================
class ServicioNomina:
    def __init__(self, repo: IRepositorio):
        self.repo = repo
    
    def _calcular_detalle_empleado(self, empleado: Empleado, id_detalle: int) -> DetalleNomina:
        return DetalleNomina(id_detalle, empleado, empleado.sueldo, Nomina.BONO, Nomina.PRESTAMO)
    
    @log_operacion
    def generar_nomina_mensual(self, aniomes: str) -> Nomina:
        empleados = self.repo.listar()
        if not empleados:
            raise ValueError("No hay empleados registrados")
        
        nomina = Nomina(id=1, aniomes=aniomes)
        nomina.detalles = [self._calcular_detalle_empleado(emp, i+1) for i, emp in enumerate(empleados)]
        nomina.calcular_totales()
        return nomina
    
    def guardar_nomina(self, nomina: Nomina) -> None:
        archivo = f"nomina_{nomina.aniomes}.json"
        data = {
            "id": nomina.id,
            "aniomes": nomina.aniomes,
            "tot_ing": nomina.tot_ing,
            "tot_des": nomina.tot_des,
            "neto": nomina.neto,
            "detalles": [
                {
                    "id": d.id,
                    "empleado": d.empleado.nombre,
                    "cedula": d.empleado.cedula,
                    "sueldo": d.sueldo,
                    "bono": d.bono,
                    "tot_ing": d.tot_ing,
                    "iess": d.iess,
                    "prestamo": d.prestamo,
                    "tot_des": d.tot_des,
                    "neto": d.neto
                } for d in nomina.detalles
            ]
        }
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Nómina guardada en {archivo}")


# ==============================
# Gestor principal
# ==============================
class GestorEmpleados:
    def __init__(self):
        self.repo = RepositorioEmpleados()
        self.servicio = ServicioNomina(self.repo)
    
    def crear_empleado(self, cedula, nombre, sueldo, departamento, cargo):
        return self.repo.crear(Empleado(cedula, nombre, sueldo, departamento, cargo))
    
    def obtener_empleado(self, cedula):
        return self.repo.obtener(cedula)
    
    def listar_empleados(self):
        return self.repo.listar()
    
    def actualizar_empleado(self, cedula, nombre, sueldo, departamento, cargo):
        return self.repo.actualizar(cedula, Empleado(cedula, nombre, sueldo, departamento, cargo))
    
    def eliminar_empleado(self, cedula):
        return self.repo.eliminar(cedula)
    
    def procesar_nomina_completa(self, aniomes):
        nomina = self.servicio.generar_nomina_mensual(aniomes)
        self.servicio.guardar_nomina(nomina)
        return {"nomina": nomina, "estadisticas": nomina.obtener_resumen().generar_estadisticas()}


# ==============================
# Menú interactivo
# ==============================
def mostrar_menu():
    print("\n=== MENÚ PRINCIPAL ===")
    print("1. Crear empleado")
    print("2. Listar empleados")
    print("3. Buscar empleado")
    print("4. Actualizar empleado")
    print("5. Eliminar empleado")
    print("6. Generar nómina mensual")
    print("7. Salir")

def main():
    gestor = GestorEmpleados()
    
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción: ")
        
        if opcion == "1":
            cedula = input("Cédula: ")
            nombre = input("Nombre: ")
            sueldo = float(input("Sueldo: "))
            dept = input("Departamento: ")
            cargo = input("Cargo: ")
            try:
                gestor.crear_empleado(cedula, nombre, sueldo, dept, cargo)
                print("✅ Empleado creado")
            except Exception as e:
                print(f"❌ {e}")
        
        elif opcion == "2":
            for emp in gestor.listar_empleados():
                print(f"{emp.cedula} - {emp.nombre} - ${emp.sueldo} - {emp.departamento} - {emp.cargo}")
        
        elif opcion == "3":
            ced = input("Cédula a buscar: ")
            emp = gestor.obtener_empleado(ced)
            print(emp.__dict__ if emp else "❌ No encontrado")
        
        elif opcion == "4":
            ced = input("Cédula a actualizar: ")
            nombre = input("Nuevo nombre: ")
            sueldo = float(input("Nuevo sueldo: "))
            dept = input("Nuevo departamento: ")
            cargo = input("Nuevo cargo: ")
            print("✅ Actualizado" if gestor.actualizar_empleado(ced, nombre, sueldo, dept, cargo) else "❌ No encontrado")
        
        elif opcion == "5":
            ced = input("Cédula a eliminar: ")
            print("✅ Eliminado" if gestor.eliminar_empleado(ced) else "❌ No encontrado")
        
        elif opcion == "6":
            aniomes = datetime.now().strftime("%Y%m")
            resultado = gestor.procesar_nomina_completa(aniomes)
            n, est = resultado["nomina"], resultado["estadisticas"]
            print(f"Nómina {n.aniomes} generada. Neto total: ${n.neto}")
            print("Estadísticas:", est)
        
        elif opcion == "7":
            print("👋 Saliendo...")
            break
        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    main()
