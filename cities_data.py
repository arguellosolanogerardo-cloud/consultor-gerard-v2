"""
Base de datos de ciudades principales por país para el sistema de login.
Incluye las ciudades más pobladas y relevantes de cada país.
"""

CIUDADES_POR_PAIS = {
    "Argentina": [
        "Buenos Aires", "Córdoba", "Rosario", "Mendoza", "San Miguel de Tucumán", 
        "La Plata", "Mar del Plata", "Salta", "Santa Fe", "San Juan", "Resistencia", 
        "Santiago del Estero", "Corrientes", "Posadas", "Neuquén", "Bahía Blanca", "San Salvador de Jujuy"
    ],
    "Bolivia": [
        "Santa Cruz de la Sierra", "El Alto", "La Paz", "Cochabamba", "Oruro", 
        "Sucre", "Tarija", "Potosí", "Sacaba", "Quillacollo"
    ],
    "Chile": [
        "Santiago", "Puente Alto", "Maipú", "La Florida", "Viña del Mar", 
        "Valparaíso", "Talcahuano", "San Bernardo", "Temuco", "Iquique", 
        "Concepción", "Rancagua", "Antofagasta", "Puerto Montt", "La Serena"
    ],
    "Colombia": [
        "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Cúcuta", 
        "Soledad", "Ibagué", "Bucaramanga", "Santa Marta", "Villavicencio", 
        "Soacha", "Pereira", "Bello", "Valledupar", "Montería", "Pasto", 
        "Manizales", "Buenaventura", "Neiva"
    ],
    "Costa Rica": [
        "San José", "Puerto Limón", "San Francisco", "Alajuela", "Liberia", 
        "Paraíso", "Desamparados", "San Isidro de El General", "Puntarenas", "Curridabat"
    ],
    "Cuba": [
        "La Habana", "Santiago de Cuba", "Camagüey", "Holguín", "Guantánamo", 
        "Santa Clara", "Las Tunas", "Bayamo", "Cienfuegos", "Pinar del Río"
    ],
    "Ecuador": [
        "Guayaquil", "Quito", "Cuenca", "Santo Domingo", "Machala", "Durán", 
        "Manta", "Portoviejo", "Loja", "Ambato", "Esmeraldas", "Quevedo"
    ],
    "El Salvador": [
        "San Salvador", "Soyapango", "Santa Ana", "San Miguel", "Mejicanos", 
        "Santa Tecla", "Apopa", "Delgado", "Sonsonate", "San Marcos"
    ],
    "España": [
        "Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga", 
        "Murcia", "Palma", "Las Palmas de Gran Canaria", "Bilbao", "Alicante", 
        "Córdoba", "Valladolid", "Vigo", "Gijón", "Hospitalet de Llobregat", 
        "Vitoria-Gasteiz", "A Coruña", "Elche", "Granada", "Terrassa", "Badalona", 
        "Oviedo", "Sabadell", "Cartagena", "Jerez de la Frontera", "Móstoles", 
        "Santa Cruz de Tenerife", "Pamplona", "Almería", "Alcalá de Henares"
    ],
    "Guatemala": [
        "Ciudad de Guatemala", "Mixco", "Villa Nueva", "Quetzaltenango", 
        "San Miguel Petapa", "Escuintla", "San Juan Sacatepéquez", "Villa Canales", 
        "Chinautla", "Chimaltenango"
    ],
    "Honduras": [
        "Tegucigalpa", "San Pedro Sula", "Choloma", "La Ceiba", "El Progreso", 
        "Choluteca", "Comayagua", "Puerto Cortés", "La Lima", "Danlí"
    ],
    "México": [
        "Ciudad de México", "Tijuana", "Ecatepec", "León", "Puebla", "Guadalajara", 
        "Juárez", "Zapopan", "Monterrey", "Nezahualcóyotl", "Chihuahua", "Mérida", 
        "Cancún", "Saltillo", "Aguascalientes", "Hermosillo", "Mexicali", 
        "San Luis Potosí", "Culiacán", "Querétaro", "Morelia", "Chimalhuacán", 
        "Reynosa", "Torreón", "Tlalnepantla", "Acapulco", "Tlaquepaque", "Guadalupe", 
        "Durango", "Tuxtla Gutiérrez", "Veracruz"
    ],
    "Nicaragua": [
        "Managua", "León", "Masaya", "Matagalpa", "Tipitapa", "Chinandega", 
        "Jinotega", "Granada", "Estelí", "Puerto Cabezas"
    ],
    "Panamá": [
        "Ciudad de Panamá", "San Miguelito", "Tocumen", "David", "Arraiján", 
        "Colón", "Las Cumbres", "La Chorrera", "Pacora", "Santiago de Veraguas"
    ],
    "Paraguay": [
        "Asunción", "Ciudad del Este", "San Lorenzo", "Luque", "Capiatá", 
        "Lambaré", "Fernando de la Mora", "Limpio", "Ñemby", "Encarnación"
    ],
    "Perú": [
        "Lima", "Arequipa", "Trujillo", "Chiclayo", "Piura", "Cusco", "Huancayo", 
        "Iquitos", "Tacna", "Juliaca", "Ica", "Cajamarca", "Pucallpa", "Sullana", 
        "Ayacucho", "Chincha Alta", "Huánuco"
    ],
    "República Dominicana": [
        "Santo Domingo", "Santiago de los Caballeros", "Santo Domingo Este", 
        "Santo Domingo Norte", "Santo Domingo Oeste", "Higüey", "San Cristóbal", 
        "San Pedro de Macorís", "La Romana", "San Francisco de Macorís"
    ],
    "Uruguay": [
        "Montevideo", "Salto", "Ciudad de la Costa", "Paysandú", "Las Piedras", 
        "Rivera", "Maldonado", "Tacuarembó", "Melo", "Mercedes"
    ],
    "Venezuela": [
        "Caracas", "Maracaibo", "Valencia", "Barquisimeto", "Ciudad Guayana", 
        "Maturín", "Maracay", "Barcelona", "Petare", "Turmero", "Ciudad Bolívar", 
        "Barinas", "Santa Teresa", "Cumaná", "San Cristóbal", "Baruta", "Puerto La Cruz"
    ],
    "United States": [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", 
        "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", 
        "Fort Worth", "Columbus", "San Francisco", "Charlotte", "Indianapolis", 
        "Seattle", "Denver", "Washington", "Boston", "El Paso", "Nashville", 
        "Detroit", "Oklahoma City", "Portland", "Las Vegas", "Memphis", "Louisville", 
        "Baltimore", "Milwaukee", "Albuquerque", "Tucson", "Fresno", "Mesa", 
        "Sacramento", "Atlanta", "Kansas City", "Colorado Springs", "Miami", "Raleigh", 
        "Omaha", "Long Beach", "Virginia Beach", "Oakland", "Minneapolis", "Tulsa", "Arlington"
    ],
    "United Kingdom": [
        "London", "Birmingham", "Manchester", "Glasgow", "Leeds", "Southampton", 
        "Liverpool", "Newcastle", "Nottingham", "Sheffield", "Bristol", "Belfast", "Leicester"
    ],
    "France": [
        "Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", 
        "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Le Havre"
    ],
    "Germany": [
        "Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", 
        "Düsseldorf", "Dortmund", "Essen", "Leipzig", "Bremen", "Dresden", "Hanover"
    ],
    "Italy": [
        "Rome", "Milan", "Naples", "Turin", "Palermo", "Genoa", "Bologna", 
        "Florence", "Bari", "Catania", "Venice", "Verona", "Messina", "Padua"
    ],
    "Brazil": [
        "São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza", 
        "Belo Horizonte", "Manaus", "Curitiba", "Recife", "Goiânia", "Belém", 
        "Porto Alegre", "Guarulhos", "Campinas", "São Luís"
    ],
    "Canada": [
        "Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton", "Ottawa", 
        "Winnipeg", "Quebec City", "Hamilton", "Kitchener", "London", "Victoria"
    ]
}

def get_cities_for_country(country_name):
    """Retorna la lista de ciudades para un país dado."""
    return CIUDADES_POR_PAIS.get(country_name, [])
