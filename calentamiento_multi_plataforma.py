#!/usr/bin/env python3
"""
🔥 CALENTAMIENTO MULTI-PLATAFORMA ULTRA-RANDOM
===============================================
Calienta cuentas de Facebook, TikTok, e Instagram simultáneamente
por dispositivo Android. Comportamiento diseñado para ser indistinguible
de un humano real.

Uso:
    # Calentar todas las plataformas en un dispositivo
    python calentamiento_multi_plataforma.py --device R38M90NT1ZH

    # Solo plataformas específicas
    python calentamiento_multi_plataforma.py --device R38M90NT1ZH --platforms tiktok,instagram

    # Múltiples dispositivos
    python calentamiento_multi_plataforma.py --devices R38M90NT1ZH,5200db1234abcd

    # Ciclos: repite N veces con sesiones y descansos entre ciclos
    python calentamiento_multi_plataforma.py --device R38M90NT1ZH --cycles 3

    # Modo continuo (hasta Ctrl+C)
    python calentamiento_multi_plataforma.py --device R38M90NT1ZH --continuous

Autor: Hermes Agent — Jul 2026
"""

import os
import sys
import time
import random
import signal
import threading
import argparse
from typing import List, Optional, Dict
from pathlib import Path

# Configurar entorno
sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

CUSTOM_ADB_PORT = int(os.getenv('CUSTOM_ADB_PORT', '5037'))
os.environ['ANDROID_ADB_SERVER_PORT'] = str(CUSTOM_ADB_PORT)

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ═══════════════════════════════════════════════════════════════

# Probabilidad de que una plataforma participe en una sesión
# (esto añade variabilidad — a veces no se calientan las 3)
PLATFORM_SESSION_PROBABILITY = {
    "tiktok": 0.85,     # 85% de las sesiones incluye TikTok
    "instagram": 0.75,  # 75% incluye Instagram
    "facebook": 0.70,   # 70% incluye Facebook
}

# Rango de duración de sesión por plataforma (minutos)
SESSION_DURATION = {
    "tiktok": (5, 35),
    "instagram": (5, 30),
    "facebook": (5, 25),
}

# Descanso entre ciclos (minutos)
CYCLE_BREAK = (10, 60)

# Tiempo entre plataformas dentro de un ciclo (segundos)
INTER_PLATFORM_DELAY = (30, 180)


# ═══════════════════════════════════════════════════════════════
# ORQUESTADOR
# ═══════════════════════════════════════════════════════════════

class WarmingOrchestrator:
    """
    Orquesta el calentamiento multi-plataforma por dispositivo.
    Cada dispositivo ejecuta las plataformas en secuencia para no
    sobrecargar uiautomator2 (que es single-threaded por conexión).
    """

    def __init__(self, device_ids: List[str], platforms: List[str],
                 cycles: int = 1, continuous: bool = False):
        self.device_ids = device_ids
        self.platforms = platforms
        self.cycles = cycles
        self.continuous = continuous
        self.stop_flags: Dict[str, threading.Event] = {}
        self.threads: List[threading.Thread] = []
        self.running = True

        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigint)

    def _handle_sigint(self, signum, frame):
        print("\n⏹️ Detención solicitada. Finalizando sesiones activas...")
        self.running = False
        for flag in self.stop_flags.values():
            flag.set()

    def _warm_device(self, device_id: str, cycle_num: int):
        """
        Ejecuta una sesión de calentamiento en un dispositivo.
        Las plataformas se ejecutan en secuencia (no paralelo) porque
        uiautomator2 no es thread-safe por conexión.
        """
        stop_flag = self.stop_flags.get(device_id, threading.Event())
        self.stop_flags[device_id] = stop_flag

        print(f"\n{'=' * 60}")
        print(f"📱 DISPOSITIVO: {device_id} | CICLO: {cycle_num}/{self.cycles if not self.continuous else '∞'}")
        print(f"{'=' * 60}")

        # Decidir qué plataformas en esta sesión (random subset)
        active_platforms = []
        for p in self.platforms:
            if random.random() < PLATFORM_SESSION_PROBABILITY.get(p, 0.8):
                active_platforms.append(p)

        # Si ninguna fue seleccionada, forzar al menos una
        if not active_platforms:
            active_platforms = [random.choice(self.platforms)]

        # Barajar orden para más variabilidad
        random.shuffle(active_platforms)
        print(f"🎯 Plataformas activas este ciclo: {active_platforms}")

        for platform in active_platforms:
            if stop_flag.is_set() or not self.running:
                break

            sesion_min, sesion_max = SESSION_DURATION.get(platform, (5, 20))
            print(f"\n--- [{platform.upper()}] Iniciando calentamiento ({sesion_min}-{sesion_max}min) ---")

            try:
                self._run_platform_warmup(device_id, platform, stop_flag)

            except Exception as e:
                print(f"❌ [{platform.upper()}][{device_id}] Error: {e}")
                import traceback
                traceback.print_exc()

            # Pausa entre plataformas
            if not stop_flag.is_set() and self.running:
                delay = random.randint(*INTER_PLATFORM_DELAY)
                print(f"⏳ Pausa {delay}s antes de siguiente plataforma...")
                time.sleep(delay)

        print(f"\n✅ [{device_id}] Ciclo {cycle_num} completado\n")

    def _run_platform_warmup(self, device_id: str, platform: str, stop_flag: threading.Event):
        """Ejecuta el calentamiento para una plataforma específica."""
        if platform == "tiktok":
            from api.utils.tiktok_automator import TiktokAutomator
            automator = TiktokAutomator(device_id, skip_reset=True)
            automator.proceso_calentamiento(detener_flag=stop_flag)

        elif platform == "instagram":
            from api.utils.instagram_automator import InstagramAutomator
            automator = InstagramAutomator(device_id, skip_reset=True)
            automator.proceso_calentamiento(detener_flag=stop_flag)

        elif platform == "facebook":
            from api.utils.facebook_automator import FacebookAutomator
            automator = FacebookAutomator(device_id)
            # Facebook usa índices secuenciales
            idx = 0
            automator.proceso_calentamiento(detener_flag=stop_flag, indice_inicial=idx)

        else:
            print(f"⚠️ Plataforma desconocida: {platform}")

    def start(self):
        """Inicia el orquestador con múltiples dispositivos."""
        print("🔥" * 30)
        print("   CALENTAMIENTO MULTI-PLATAFORMA ULTRA-RANDOM")
        print("🔥" * 30)
        print(f"📱 Dispositivos: {self.device_ids}")
        print(f"🎯 Plataformas: {self.platforms}")
        print(f"🔄 Ciclos: {'infinito' if self.continuous else self.cycles}")
        print(f"🎲 Comportamiento: totalmente aleatorio")
        print("🔥" * 30)

        cycle = 0
        while self.running and (self.continuous or cycle < self.cycles):
            cycle += 1

            if not self.continuous and cycle > self.cycles:
                break

            # Lanzar un thread por dispositivo
            self.threads = []
            for did in self.device_ids:
                t = threading.Thread(
                    target=self._warm_device,
                    args=(did, cycle),
                    daemon=True,
                    name=f"warming-{did}"
                )
                t.start()
                self.threads.append(t)

            # Esperar que todos terminen este ciclo
            for t in self.threads:
                while t.is_alive() and self.running:
                    t.join(timeout=5)

            # Descanso entre ciclos
            if self.running and (self.continuous or cycle < self.cycles):
                break_min = random.randint(*CYCLE_BREAK)
                print(f"\n😴 DESCANSANDO {break_min} minutos entre ciclos...")
                break_end = time.time() + (break_min * 60)
                while time.time() < break_end and self.running:
                    time.sleep(min(30, break_end - time.time()))

        print("\n✅ Calentamiento completado. Todas las cuentas calientes. 🔥")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🔥 Calentamiento de cuentas multi-plataforma ultra-random"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--device", "-d", help="Device ID (ADB serial)")
    group.add_argument("--devices", help="Device IDs separados por coma")

    parser.add_argument(
        "--platforms", "-p",
        default="tiktok,instagram,facebook",
        help="Plataformas a calentar (default: tiktok,instagram,facebook)"
    )
    parser.add_argument(
        "--cycles", "-c",
        type=int, default=1,
        help="Número de ciclos (default: 1)"
    )
    parser.add_argument(
        "--continuous", "--infinito",
        action="store_true",
        help="Modo continuo hasta Ctrl+C"
    )

    args = parser.parse_args()

    # Parsear dispositivos
    if args.device:
        device_ids = [args.device]
    else:
        device_ids = [d.strip() for d in args.devices.split(",") if d.strip()]

    if not device_ids:
        print("❌ Se requiere al menos un dispositivo")
        sys.exit(1)

    # Parsear plataformas
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    valid = {"tiktok", "instagram", "facebook"}
    platforms = [p for p in platforms if p in valid]
    if not platforms:
        print(f"❌ Plataformas válidas: {valid}")
        sys.exit(1)

    orchestrator = WarmingOrchestrator(
        device_ids=device_ids,
        platforms=platforms,
        cycles=args.cycles,
        continuous=args.continuous
    )
    orchestrator.start()


if __name__ == "__main__":
    main()
