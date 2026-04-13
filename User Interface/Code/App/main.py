from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from datetime import datetime, timedelta
from time import time
import qrcode
import holidays
import requests
import cv2

animal_info = {
    "Lion":"The lion is a powerful carnivorous mammal known for its strength, social nature, and distinctive appearance, especially the male’s thick mane. It is mainly found in parts of Africa and a small population in India’s Gir Forest. Unlike most big cats, lions live in groups called prides, which include females, cubs, and a few males, with females usually doing the hunting in coordinated groups. They prey on large animals like deer and antelope and spend much of their time resting to conserve energy. Lions communicate through loud roars that help them mark territory and stay connected with their pride. Due to threats like habitat loss and human conflict, their population has declined, making conservation efforts important for their survival.",
    "Giraffe":"The giraffe is the tallest land animal on Earth, recognized by its long neck and legs, which help it reach leaves high in trees, especially acacia. It is native to Africa and usually lives in loose social groups. Giraffes are herbivores and spend much of their day feeding, using their long tongues to strip leaves, and they rely on their height to spot predators from a distance.",
    "Tiger":"The tiger is the largest of all wild cats and is known for its striking orange coat with black stripes. Found mainly in Asia, tigers are solitary and highly territorial animals. They are powerful hunters that prey on deer and other large animals, using stealth and strength to ambush their targets, and they are excellent swimmers compared to other big cats.",
    "Camel":"The camel is well adapted to desert environments and is known for its humps, which store fat that can be converted into energy and water. Camels can survive long periods without drinking water and can تحمل extreme temperatures. They are commonly used by humans for transport in arid regions and are known for their endurance and ability to travel long distances.",
    "Bull":"The bull is an adult male of the cattle species, known for its strength, muscular build, and sometimes aggressive behavior. Bulls have been used in agriculture for breeding and labor, and in some cultures, they play important roles in traditional events and sports. They are herbivores and typically graze on grass and other vegetation.",
    "Polar Bear":"The polar bear is a large carnivorous mammal that lives in the Arctic region and is well adapted to cold environments with its thick fur and layer of fat. It primarily hunts seals and is an excellent swimmer, often traveling long distances across icy waters. Polar bears depend heavily on sea ice for hunting and survival, and climate change poses a major threat to their habitat."
}
holidays = holidays.India()
bookings = []

def generate_qr(amount):
    upi_id = "UPI_ID"
    name = "NAME_ON_QR"

    upi_link = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"

    img = qrcode.make(upi_link)
    img.save("payment_qr.png")

    return "payment_qr.png"

class SelfPopup(Popup):
    pass

class SafariPopup(Popup):
    pass

class WarningPopup(Popup):
    pass

class TicketPopup(Popup):
    ticket_index = None

    def toggle_button(self, is_active):
        btn = self.ids.start_btn
        btn.disabled = not is_active

    def start_safari(self):
        root = App.get_running_app().root
        booking = bookings[self.ticket_index - 1]

        try:
            requests.post("http://SERVER_IP_ADD:5000/assign_car",
                          json={"name": root.user_name})

            data = {
                "name": booking["name"],
                "date": booking["date"],
                "time": booking["slot"]
            }

        except Exception as e:
            print("Error deleting booking:", e)

        root.remove_ticket(self.ticket_index)

        self.dismiss()
        root.show_safari()

class BookingPopup(Popup):
    price_per_seat = 200
    remaining_seats = 60

    def send_booking(self):
        url = "http://SERVER_IP_ADD:5000/book"

        try:
            name = self.ids.name_input.text.strip()
            seats = int(self.ids.seats_input.text)

            total_text = self.ids.total_label.text.replace("Total: ₹", "")
            price = int(total_text)

            app = App.get_running_app()

            data = {
                "name": name,
                "visit_date": app.selected_date,
                "time": app.selected_slot,
                "seats": seats,
                "price": price
            }

            response = requests.post(url, json=data)
            print(response.json())

        except Exception as e:
            print("Error sending booking:", e)

    def validate_booking(self):
        name = self.ids.name_input.text.strip()
        seats_text = self.ids.seats_input.text.strip()

        if name and seats_text:
            try:
                seats = int(seats_text)

                if seats <= self.remaining_seats:
                    self.ids.confirm_btn.disabled = False
                else:
                    self.ids.confirm_btn.disabled = True

            except:
                self.ids.confirm_btn.disabled = True
        else:
            self.ids.confirm_btn.disabled = True

    def calculate_total(self):
        try:
            seats = int(self.ids.seats_input.text)
            total = seats * self.price_per_seat
            self.ids.total_label.text = f"Total: ₹{total}"

            qr_path = generate_qr(total)
            self.ids.qr_image.source = qr_path
            self.ids.qr_image.reload()
        except:
            self.ids.total_label.text = "Enter valid number"

    def confirm_booking(self):
        try:
            name = self.ids.name_input.text.strip()
            seats = int(self.ids.seats_input.text)
            total = seats * self.price_per_seat

            app = App.get_running_app()
            visit_date = app.selected_date
            slot = app.selected_slot

            self.send_booking()

            booking_data = {
                "name": name,
                "seats": seats,
                "total": total,
                "date": visit_date,
                "slot": slot
            }

            bookings.append(booking_data)

            App.get_running_app().root.update_ticket_screen()

            self.dismiss()

            App.get_running_app().root.show_booking()

        except:
            print("Invalid booking")

class ReportLayout(BoxLayout):
    def on_kv_post(self, base_widget):
        from time import time

        app = App.get_running_app()

        elapsed = int(time() - app.safari_start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60

        objects = app.detected_objects if hasattr(app, "detected_objects") else []

        logs = app.car_data_log if hasattr(app, "car_data_log") else []

        if logs:
            last = logs[-1]
            lat = last.get("lat")
            lon = last.get("lon")
            aqi = last.get("aqi")
        else:
            lat = lon = aqi = "N/A"

        report = f"""
SAFARI REPORT

Time Elapsed: {minutes:02d}:{seconds:02d}

Last Location:
Latitude: {lat}
Longitude: {lon}

Air Quality Index: {aqi}

Animals Detected:
{', '.join(objects) if objects else "None"}
        """

        self.ids.Report.text = report

class BookingLayout(BoxLayout):
    def get_remaining_seats(self, date, time):
        try:
            url = "http://SERVER_IP_ADD:5000/availability"
            params = {"date": date, "time": time}

            response = requests.get(url, params=params)
            data = response.json()

            return int(data["remaining"])

        except:
            return 60

    def initialize_slots(self):
        today = datetime.today()

        for i in range(7):
            date_obj = today + timedelta(days=i)
            date = date_obj.strftime("%Y-%m-%d")
            self.ids[f"day{i}"].text = date

            is_tuesday = date_obj.weekday() in [1]
            is_holiday = date_obj in holidays

            if is_tuesday or is_holiday:
                self.ids[f"day{i}buttons"].disabled = True
                self.ids[f"day{i}buttons"].clear_widgets()
                self.ids[f"day{i}buttons"].add_widget(Label(text="Holiday"))

            times = ['09:00:00', '14:00:00', '18:00:00']

            for j, btn in enumerate(self.ids[f"day{i}buttons"].children[::-1]):
                remaining = self.get_remaining_seats(date, times[j])

                btn.text = str(remaining)

                if remaining <= 0:
                    btn.disabled = True

    def on_kv_post(self, base_widget):
        self.initialize_slots()

class HomeLoginLayout(BoxLayout):
    def validate_signin(self):
        name = self.ids.name_input.text.strip()
        mob = self.ids.mob_input.text.strip()
        email = self.ids.email_input.text.strip()

        if name and mob and email:
            self.ids.signin_button.disabled = False
        else:
            self.ids.signin_button.disabled = True

    def send_login(self):
        url = "http://SERVER_IP_ADD:5000/login"

        data = {
            "name": self.ids.name_input.text.strip(),
            "mobile": self.ids.mob_input.text.strip(),
            "email": self.ids.email_input.text.strip()
        }

        try:
            response = requests.post(url, json=data)
            print("Login response:", response.text)
        except Exception as e:
            print("Login error:", e)

class HomeUserLayout(BoxLayout):
    pass

class SafariLayout(BoxLayout):
    def on_kv_post(self, base_widget):
        from ultralytics import YOLO

        self.model = YOLO("best.pt")
        self.cap = cv2.VideoCapture(0)

        App.get_running_app().safari_start_time = time()
        App.get_running_app().detected_objects = []
        App.get_running_app().car_data_log = []

        Clock.schedule_interval(self.update_frame, 1 / 10)
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_interval(self.update_location, 1)
        Clock.schedule_interval(self.store_car_data, 5)

    def store_car_data(self, dt):
        import random

        #took random values for testing the App
        App.get_running_app().car_data_log.append({
            "lat": round(random.uniform(18.8, 19.3), 6),
            "lon": round(random.uniform(72.7, 73.1), 6),
            "aqi": random.randint(50, 200)
        })

    def show_info(self, obj):
        self.ids.info_label.text = animal_info.get(obj, "Unknown animal")

    def update_location(self, dt):
        app = App.get_running_app()

        if app.car_data_log:
            last = app.car_data_log[-1]

            lat = last.get("lat")
            lon = last.get("lon")

            self.ids.location_label.text = f"Lat: {lat} | Lon: {lon}"
        else:
            self.ids.location_label.text = "Lat: -- | Lon: --"

    def update_frame(self, dt):
        ret, frame = self.cap.read()
        if not ret:
            return

        results = self.model(frame)

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                obj_name = self.model.names[cls]

                # Call detection logic
                self.object_detected(obj_name)

        annotated_frame = results[0].plot()

        buf = cv2.flip(annotated_frame, 0).tobytes()
        texture = Texture.create(size=(annotated_frame.shape[1], annotated_frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')

        self.ids.cam_feed.texture = texture

    def object_detected(self, obj_name):
        import requests

        requests.post("http://SERVER_IP_ADD:5000/set_command",
                      json={"command": "STOP"})

        self.ids.Move_btn.disabled = False

        app = App.get_running_app()

        if obj_name not in app.detected_objects:
            app.detected_objects.append(obj_name)

            self.show_info(obj_name)

        if not hasattr(self, "detected_objects"):
            self.detected_objects = []

        self.detected_objects.append(obj_name)

    def move_car(self):
        import requests
        requests.post("http://SERVER_IP_ADD:5000/set_command",
                      json={"command": "MOVE"})

        self.ids.Move_btn.disabled = True

    def update_time(self, dt):
        from time import time

        elapsed = int(time() - App.get_running_app().safari_start_time)

        minutes = elapsed // 60
        seconds = elapsed % 60

        self.ids.time_label.text = f"Time Elapsed : {minutes:02d}:{seconds:02d}"

class TicketLayout(BoxLayout):
    pass

class MainWidget(BoxLayout):
    user_name = ""

    def load_user_bookings(self):
        global bookings

        try:
            url = "http://SERVER_IP_ADD:5000/get_bookings"
            params = {"name": self.user_name}

            print("Sending name:", self.user_name)

            response = requests.get(url, params=params)

            print("Status:", response.status_code)
            print("Response:", response.text)

            if response.status_code == 200:
                data = response.json()
                bookings.clear()

                for b in data:
                    booking_data = {
                        "name": b["Name"],
                        "seats": b["Seats"],
                        "total": b["Price"],
                        "date": str(b["Date"]),
                        "slot": str(b["Time"])
                    }
                    bookings.append(booking_data)

            else:
                print("Server error:", response.text)

        except Exception as e:
            print("Error loading bookings:", e)

    def remove_ticket(self, index):
        if 0 <= index-1 < len(bookings):
            bookings.pop(index-1)

        self.update_ticket_screen()

    def update_ticket_screen(self):
        if not hasattr(self, "ticket_layout"):
            return

        layout = self.ticket_layout

        for i in range(1, 5):
            ticket = layout.ids[f"ticket{i}"]
            ticket.opacity = 0
            ticket.disabled = True

        if not bookings:
            layout.ids.no_ticket.opacity = 1
            layout.ids.max_ticket.opacity = 0
            return

        layout.ids.no_ticket.opacity = 0

        for i, b in enumerate(bookings[:4]):
            ticket = layout.ids[f"ticket{i + 1}"]
            layout.ids[f"person{i + 1}"].text = f"Name: {b['name']}"
            layout.ids[f"date{i + 1}"].text = f"Date: {b['date']}"
            layout.ids[f"slot{i + 1}"].text = f"Time Slot: {b['slot']}"
            layout.ids[f"seat{i + 1}"].text = f"Seats: {b['seats']}"
            layout.ids[f"price{i + 1}"].text = f"Price: ₹{b['total']}"
            ticket.opacity = 1
            ticket.disabled = False

        if len(bookings) >= 4:
            layout.ids.max_ticket.opacity = 1
        else:
            layout.ids.max_ticket.opacity = 0

    def show_login_home(self):
        self.ids.container.clear_widgets()
        self.ids.container.add_widget(HomeLoginLayout())


    def show_user_home(self, name=None):

        if name:
            self.user_name = name.strip()

        self.ids.container.clear_widgets()

        user = HomeUserLayout()
        user.ids.welcome_label.text = f"Hi! {self.user_name}"

        self.ids.container.add_widget(user)
        self.load_user_bookings()
        self.update_ticket_screen()

    def show_booking(self):
        self.ids.container.clear_widgets()
        self.ids.container.add_widget(BookingLayout())

    def show_safari(self):
        self.ids.container.clear_widgets()
        self.ids.container.add_widget(SafariLayout())

    def show_report(self):
        self.ids.container.clear_widgets()
        self.ids.container.add_widget(ReportLayout())

    def show_ticket(self):
        self.ids.container.clear_widgets()
        self.ticket_layout = TicketLayout()
        self.ids.container.add_widget(self.ticket_layout)

        self.update_ticket_screen()

class TheSafariApp(App):
    selected_date = ''
    selected_slot = ''

    def build(self):
        root = MainWidget()
        root.show_login_home()
        return root

    def open_warning_popup(self):
        popup = WarningPopup()
        popup.open()

    def open_booking_popup(self, date, slot, remaining):
        self.selected_date = date
        self.selected_slot = slot
        popup = BookingPopup()
        popup.remaining_seats = int(remaining)
        popup.open()

    def open_safari_popup(self):
        popup = SafariPopup()
        popup.open()

    def open_self_popup(self):
        popup = SelfPopup()
        popup.open()

    def open_ticket_popup(self, ticket_index):
        popup = TicketPopup()
        popup.ticket_index = ticket_index
        popup.open()

TheSafariApp().run()