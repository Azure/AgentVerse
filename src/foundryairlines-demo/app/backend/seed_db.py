#!/usr/bin/env python3
"""
FoundryAirlines Demo - Flight Database Seeder
Creates and populates flights.db with realistic FoundryAirlines flight data.
"""

import sqlite3
import os
from datetime import datetime, timedelta

# Base date for demo: 2026-05-07
BASE_DATE = datetime(2026, 5, 7)

# FoundryAirlines realistic routes from Spanish hubs
FLIGHTS_DATA = [
    # Low occupancy flights (35-55%) - target for demo
    ("VY8401", "BCN", "BER", "Berlin", "Germany", 12, 180, 64, 79.00),
    ("VY3215", "MAD", "VIE", "Vienna", "Austria", 8, 174, 78, 89.00),
    ("VY6742", "VLC", "PRG", "Prague", "Czech Republic", 15, 186, 93, 69.00),
    ("VY2891", "AGP", "DUB", "Dublin", "Ireland", 20, 168, 74, 99.00),
    ("VY5623", "BIO", "CPH", "Copenhagen", "Denmark", 18, 180, 99, 119.00),
    
    # Medium occupancy flights (60-80%)
    ("VY1234", "BCN", "CDG", "Paris", "France", 5, 186, 130, 89.00),
    ("VY2345", "MAD", "FCO", "Rome", "Italy", 7, 174, 121, 99.00),
    ("VY3456", "BCN", "LGW", "London", "United Kingdom", 10, 180, 126, 109.00),
    ("VY4567", "VLC", "AMS", "Amsterdam", "Netherlands", 14, 186, 139, 95.00),
    ("VY5678", "PMI", "ORY", "Paris", "France", 6, 168, 101, 79.00),
    ("VY6789", "SVQ", "LIS", "Lisbon", "Portugal", 9, 180, 135, 59.00),
    ("VY7890", "MAD", "MUC", "Munich", "Germany", 11, 174, 122, 119.00),
    ("VY8901", "BCN", "BRU", "Brussels", "Belgium", 13, 186, 148, 85.00),
    ("VY9012", "AGP", "ZRH", "Zurich", "Switzerland", 16, 168, 118, 139.00),
    ("VY1122", "BIO", "ATH", "Athens", "Greece", 19, 180, 126, 129.00),
    
    # High occupancy flights (85-95%)
    ("VY2233", "BCN", "FCO", "Rome", "Italy", 4, 186, 167, 119.00),
    ("VY3344", "MAD", "LHR", "London", "United Kingdom", 3, 174, 157, 149.00),
    ("VY4455", "BCN", "AMS", "Amsterdam", "Netherlands", 2, 186, 172, 109.00),
    ("VY5566", "VLC", "CDG", "Paris", "France", 1, 180, 162, 99.00),
    ("VY6677", "PMI", "BER", "Berlin", "Germany", 8, 168, 151, 89.00),
    ("VY7788", "MAD", "LIS", "Lisbon", "Portugal", 6, 174, 156, 69.00),
    ("VY8899", "BCN", "VIE", "Vienna", "Austria", 17, 186, 167, 129.00),
    ("VY9900", "AGP", "LGW", "London", "United Kingdom", 21, 168, 155, 139.00),
    ("VY1011", "SVQ", "ORY", "Paris", "France", 25, 180, 162, 79.00),
    ("VY1213", "BIO", "MUC", "Munich", "Germany", 28, 174, 157, 149.00),
]


def create_database():
    """Create and populate the flights database."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "flights.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop and recreate table for idempotency
    cursor.execute("DROP TABLE IF EXISTS flights")
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            destination_city TEXT NOT NULL,
            destination_country TEXT NOT NULL,
            date TEXT NOT NULL,
            total_seats INTEGER NOT NULL,
            sold_seats INTEGER NOT NULL,
            price_eur REAL NOT NULL
        )
    """)
    
    # Insert flight data
    for code, origin, dest, city, country, days_offset, total, sold, price in FLIGHTS_DATA:
        flight_date = (BASE_DATE + timedelta(days=days_offset)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO flights 
            (code, origin, destination, destination_city, destination_country, date, total_seats, sold_seats, price_eur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, origin, dest, city, country, flight_date, total, sold, price))
    
    conn.commit()
    
    # Query and display 5 lowest occupancy flights
    cursor.execute("""
        SELECT code, origin, destination, destination_city, date, 
               total_seats, sold_seats, 
               ROUND(100.0 * sold_seats / total_seats, 1) as occupancy_pct,
               price_eur
        FROM flights
        ORDER BY occupancy_pct ASC
        LIMIT 5
    """)
    
    print("\n" + "="*80)
    print("FOUNDRYAIRLINES FLIGHT DATABASE SEEDED SUCCESSFULLY")
    print("="*80)
    print(f"\nDatabase location: {db_path}")
    print(f"Total flights inserted: {len(FLIGHTS_DATA)}")
    print("\n🎯 5 LOWEST OCCUPANCY FLIGHTS (Demo Targets):")
    print("-"*80)
    print(f"{'Code':<8} {'Route':<12} {'City':<15} {'Date':<12} {'Occupancy':<12} {'Price'}")
    print("-"*80)
    
    for row in cursor.fetchall():
        code, origin, dest, city, date, total, sold, occ_pct, price = row
        route = f"{origin}→{dest}"
        occupancy_str = f"{sold}/{total} ({occ_pct}%)"
        print(f"{code:<8} {route:<12} {city:<15} {date:<12} {occupancy_str:<12} €{price:.2f}")
    
    print("="*80 + "\n")
    
    conn.close()


if __name__ == "__main__":
    create_database()
