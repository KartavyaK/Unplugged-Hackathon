from flask import Flask, request, jsonify
import mysql.connector
from datetime import date
import requests

car_command = "STOP"

app = Flask(__name__)
    
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="SQL_PASSWORD",
        database="DATABASE_NAME"
    )

@app.route('/assign_car', methods=['POST'])
def assign_car():
    name = request.json['name']

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT Car_ID FROM Car_Table WHERE Name IS NULL LIMIT 1")
    car = cursor.fetchone()

    if car:
        cursor.execute("UPDATE Car_Table SET Name=%s WHERE Car_ID=%s", (name, car[0]))
        db.commit()
        return jsonify({"car_id": car[0]})

    return jsonify({"error": "No car available"})

@app.route('/car_data', methods=['GET'])
def car_data():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Car_Table WHERE Car_ID=1")
    data = cursor.fetchone()

    return jsonify(data)

@app.route('/set_command', methods=['POST'])
def set_command():
    global car_command
    data = request.json
    car_command = data['command']
    return jsonify({"status": "ok"})


@app.route('/get_command', methods=['GET'])
def get_command():
    return jsonify({"command": car_command})

@app.route('/data', methods=['POST'])
def receive():
    try:
        data = request.json  

        db = get_db_connection()
        cursor = db.cursor()

        rfid = data['rfid']
        lat = data['lat']
        lon = data['lon']
        aqi = data['aqi']

        print("RFID:", rfid, "Lat:", lat, "Lon:", lon, "AQI:", aqi)
        
        query = """
        UPDATE Car_Table
        SET RFID_State = %s,
            AQI_Value = %s,
            latitude = %s,
            longitude = %s
        WHERE Car_ID = 1
        """

        cursor.execute(query, (rfid, aqi, lat, lon))
        db.commit()

        print("Database Updated!")

        return "OK"

    except Exception as e:
        print("Error:", e)
        return "Error", 400

@app.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.json

        name = data['name']
        mobile = data['mobile']
        email = data['email']

        db = get_db_connection()
        cursor = db.cursor()

        query = """
        INSERT INTO users (name, mobile_number, email)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        mobile_number = VALUES(mobile_number)
        """

        cursor.execute(query, (name, mobile, email))
        db.commit()

        cursor.close()
        db.close()

        return jsonify({"message": "User stored"})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/book', methods=['POST'])
def book_ticket():
    try:
        db = get_db_connection()
        cursor = db.cursor()

        data = request.json
        booking_date = date.today()

        query = """
        INSERT INTO Slots_Table (Name, Date_of_Booking, Date, Time, Seats, Price)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            data['name'],
            booking_date,
            data['visit_date'],
            data['time'],
            data['seats'],
            data['price']
        )

        cursor.execute(query, values)
        db.commit()

        cursor.close()
        db.close()

        return jsonify({"message": "Booking successful"})

    except Exception as e:
        print("SERVER ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/availability', methods=['GET'])
def get_availability():
    try:
        db = get_db_connection()
        cursor = db.cursor()

        date_val = request.args.get('date')
        time_val = request.args.get('time')

        query = """
        SELECT SUM(Seats) FROM Slots_Table
        WHERE Date = %s AND Time = %s
        """

        cursor.execute(query, (date_val, time_val))
        result = cursor.fetchone()[0]

        booked = result if result else 0
        remaining = 60 - booked

        cursor.close()
        db.close()

        return jsonify({
            "booked": booked,
            "remaining": remaining
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/bookings', methods=['GET'])
def get_all_bookings():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Slots_Table")
    result = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(result)

@app.route('/delete_booking', methods=['POST'])
def delete_booking():
    try:
        data = request.json

        name = data['name']
        date_val = data['date']
        time_val = data['time']

        db = get_db_connection()
        cursor = db.cursor()

        query = """
        DELETE FROM Slots_Table
        WHERE Name = %s AND Date = %s AND Time = %s
        LIMIT 1
        """

        cursor.execute(query, (name, date_val, time_val))
        db.commit()

        cursor.close()
        db.close()

        return jsonify({"message": "Booking deleted"})

    except Exception as e:
        print("DELETE ERROR:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/get_bookings', methods=['GET'])
def get_user_bookings():
    try:
        name = request.args.get('name')

        if not name:
            return jsonify({"error": "Name is required"}), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        query = "SELECT * FROM Slots_Table WHERE Name = %s"
        cursor.execute(query, (name,))
        results = cursor.fetchall()

        for row in results:
            for key in row:
                if isinstance(row[key], (date,)):
                    row[key] = str(row[key])
                elif hasattr(row[key], 'total_seconds'):
                    row[key] = str(row[key])
                else:
                    row[key] = str(row[key])

        cursor.close()
        db.close()

        return jsonify(results)

    except Exception as e:
        print("SERVER ERROR:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)