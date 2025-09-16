import requests

# Aktualisierte Liste der Städte
cities = [
    "Shanghai", "New Delhi", "Karatschi", "Peking", "Shenzhen", "Kinshasa", "Guangzhou", "Lagos",
    "İstanbul", "Bengaluru", "Chengdu", "Mumbai", "Moskau", "Lahore", "São Paulo", "Tianjin",
    "Jakarta", "Wuhan", "Dhaka", "Hyderabad", "Kairo", "Tokio", "Chennai", "Lima", "Dongguan",
    "Seoul", "Chongqing", "Xi’an", "Hangzhou", "Luanda", "Foshan", "Teheran", "London", "Mexiko-Stadt",
    "New York City", "Ahmedabad", "Bogotá", "Surat", "Nanjing", "Hongkong", "Shenyang", "Ho-Chi-Minh-Stadt",
    "Riad", "Bagdad", "Rio de Janeiro", "Zhengzhou", "Qingdao", "Kolkata", "Suzhou", "Singapur",
    "Bangkok", "Changsha", "Abidjan", "Sankt Petersburg", "Jinan", "Daressalam", "Kunming", "Alexandria",
    "Harbin", "Sydney", "Santiago de Chile", "Ankara", "Shijiazhuang", "Hefei", "Melbourne", "Dalian",
    "Johannesburg", "Cape Town", "Rangun", "Xiamen", "Nanning", "Changchun", "Kabul", "Nairobi",
    "Gizeh", "Kano", "Taiyuan", "eThekwini", "Bamako", "Jaipur", "Ekurhuleni", "Tshwane",
    "Neu-Taipeh", "Guiyang", "Wuxi", "Pune", "Shantou", "Ibadan", "Ürümqi", "Los Angeles",
    "Zhongshan", "Abuja", "Lucknow", "Yokohama", "Berlin", "Ningbo", "Fuzhou", "Dschidda",
    "Hanoi", "Nanchang", "Addis Abeba", "Port Harcourt", "Casablanca", "Busan", "Madrid",
    "Dubai", "Chittagong", "Faisalabad", "Kanpur", "Changzhou", "Buenos Aires", "Pjöngjang",
    "Lanzhou", "Maschhad"
]

# Dateiname für die Ausgabe
output_file = "gs_file.txt"


def get_coordinates(city):
    """Ruft die Koordinaten einer Stadt mithilfe der Nominatim API ab."""
    url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json"
    response = requests.get(url)
    data = response.json()
    if data:
        return data[0]["lon"], data[0]["lat"]
    else:
        return None, None


# Schreiben der Koordinaten in eine Datei
with open(output_file, 'w') as file:
    for city in cities:
        lon, lat = get_coordinates(city)
        if lon and lat:
            file.write(f"{lon}, {lat}\n")
        else:
            print(f"Koordinaten für {city} konnten nicht gefunden werden.")

print(f"Koordinaten wurden erfolgreich in {output_file} geschrieben.")
