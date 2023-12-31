from flask import *
from dotenv import load_dotenv
import mysql.connector.pooling, json, jwt, datetime, time, requests, os

# 設置環境變數
load_dotenv()
db_password = os.getenv("db_password")
secret_key = os.getenv("jwt_secret_key")
tappay_partner_key = os.getenv("tappay_partner_key")
tappay_merchant_id = os.getenv("tappay_merchant_id")

dbconfig = {
    "user" : "root",
    "password" : db_password,
    "host" : "localhost",
    "database" : "taipei_day_trip"
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="pool", pool_size=10, **dbconfig)

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["JSON_AS_ASCII"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["JSON_SORT_KEYS"] = False

# Pages
@app.route("/")
def index():
	return render_template("index.html")

@app.route("/attraction/<id>")
def attraction(id):
	return render_template("attraction.html")

@app.route("/booking")
def booking():
	return render_template("booking.html")

@app.route("/thankyou")
def thankyou():
	return render_template("thankyou.html")

# Function（用 id 比對後將 url 統整成 list）
def create_images_list():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		cursor.execute("SELECT attractions_id, url FROM images")
		url_data = cursor.fetchall()

		final_data = {}
		for detail in url_data:
			id = detail["attractions_id"]
			url = detail["url"]

			if id in final_data:
				final_data[id]["url"].append(url)
			else:
				final_data[id] = {"id": id, "url": [url]}

		result = list(final_data.values())
		return result
	except Exception as error:
		print(error)
		connection.rollback()
	finally:
		cursor.close()
		connection.close()		

# Function（把 url 的 list 加入資料）
def add_images_to_data(data, result):		
		for compare_data in data:
			data_id = compare_data["id"]

			for images_data in result:
				if data_id == images_data["id"]:
					compare_data["images"] = images_data["url"]
		return data

# API
@app.route("/api/attractions")
def attractions_list():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		page = int(request.args.get("page", 0))
		keyword = request.args.get("keyword", None)

		offset = page * 12
		nextoffset = (page+1) * 12

		if keyword is None:
			query = """
			SELECT a.id, a.name, a.description, a.address, a.transport, a.lat, a.lng, c.name AS category, m.name AS mrt
			FROM attractions AS a
			INNER JOIN category AS c ON a.category_id=c.id
			INNER JOIN mrt AS m ON a.mrt_id=m.id
			ORDER BY a.id ASC
			LIMIT 12 OFFSET %s
			"""
			cursor.execute(query, (offset,))
			data = cursor.fetchall()

			cursor.execute(query, (nextoffset,))
			nextdata = cursor.fetchall()

			result = create_images_list()
			final_data = add_images_to_data(data, result)

			if nextdata:
				return jsonify({"nextPage" : page + 1, "data" : final_data})
			else:
				return jsonify({"nextPage" : None, "data" : final_data})				
		else:
			check_keyword = """
			SELECT a.id, a.name, a.description, a.address, a.transport, a.lat, a.lng, c.name AS category, m.name AS mrt
			FROM attractions AS a
			INNER JOIN category AS c ON a.category_id=c.id
			INNER JOIN mrt AS m ON a.mrt_id=m.id
			WHERE m.name=%s OR a.name LIKE %s
			ORDER BY a.id ASC
			LIMIT 12 OFFSET %s
			"""
			cursor.execute(check_keyword, (keyword, "%" + keyword + "%", offset))
			data = cursor.fetchall()

			cursor.execute(check_keyword, (keyword, "%" + keyword + "%", nextoffset))
			nextdata = cursor.fetchall()

			result = create_images_list()
			final_data = add_images_to_data(data, result)

			if nextdata:
				return jsonify({"nextPage" : page + 1, "data" : final_data})
			else:
				return jsonify({"nextPage" : None, "data" : final_data})				
	except Exception as error:
		print(error)
		connection.rollback()

		error_data = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}
		return jsonify(error_data), 500
	finally:
		cursor.close()
		connection.close()

@app.route("/api/attraction/<int:attractionId>")
def attractions_id(attractionId):
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		query = """
		SELECT a.id, a.name, a.description, a.address, a.transport, a.lat, a.lng, c.name AS category, m.name AS mrt
		FROM attractions AS a
		INNER JOIN category AS c ON a.category_id=c.id
		INNER JOIN mrt AS m ON a.mrt_id=m.id
		WHERE a.id=%s
		"""
		cursor.execute(query, (attractionId, ))
		data = cursor.fetchall()

		if not data:
			attractionId_not_found = {
				"error": True,
				"message": "景點編號不正確"
			}
			return jsonify(attractionId_not_found), 400
		else:
			result = create_images_list()
			final_data = add_images_to_data(data, result)

			return jsonify({"data" : final_data[0]})
	except Exception as error:
		print(error)
		connection.rollback()

		error_data = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}
		return jsonify(error_data), 500
	finally:
		cursor.close()
		connection.close()

@app.route("/api/mrts")
def mrts_list():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		query = """
		SELECT m.name AS mrt
		FROM attractions AS a
		INNER JOIN mrt AS m ON a.mrt_id=m.id
		GROUP BY mrt
		ORDER BY COUNT(*) DESC
		"""
		cursor.execute(query)
		data = cursor.fetchall()

		final_data = []
		for detail in data:
			mrt_name = detail["mrt"]
			if mrt_name != "沒有資料":
				final_data.append(mrt_name)

		return jsonify({"data" : final_data})		
	except Exception as error:
		print(error)
		connection.rollback()

		error_data = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}
		return jsonify(error_data), 500		
	finally:
		cursor.close()
		connection.close()

@app.route("/api/user", methods=["POST"])
def create_user():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)	

	try:
		data = request.get_json()
		name = data["name"]
		email = data["email"]
		password = data["password"]

		query = "SELECT email FROM users WHERE email=%s"
		cursor.execute(query, (email, ))
		select_data = cursor.fetchall()

		if not name or not email or not password:
			wrong_message = {
				"error": True,
				"message": "註冊資料不得為空"
			}

			return jsonify(wrong_message), 400
		elif not select_data:
			query = "INSERT INTO users(name, email, password) VALUES(%s, %s, %s)"
			cursor.execute(query, (name, email, password))
			connection.commit()

			return jsonify({"ok" : True}), 200
		else:
			wrong_message = {
				"error": True,
				"message": "此Email已被註冊過"
			}

			return jsonify(wrong_message), 400			
	except Exception as error:
		print(error)
		connection.rollback()

		error_message = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}
		return jsonify(error_message), 500		
	finally:
		cursor.close()
		connection.close()

@app.route("/api/user/auth", methods=["PUT"])
def login():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)	

	try:
		data = request.get_json()
		email = data["email"]
		password = data["password"]

		query = "SELECT id, email, password FROM users WHERE email=%s"
		cursor.execute(query, (email, ))
		select_data = cursor.fetchone()

		if select_data and password == select_data["password"]:
			payload = {
				"id": select_data["id"],
				"exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
			}
			token = jwt.encode(payload, secret_key, algorithm="HS256")

			return jsonify({"token" : token}), 200
		elif select_data and password != select_data["password"]:
			wrong_message = {
				"error": True,
				"message": "密碼輸入錯誤"
			}

			return jsonify(wrong_message), 400
		elif not select_data:
			wrong_message = {
				"error": True,
				"message": "Email輸入錯誤"
			}

			return jsonify(wrong_message), 400
	except Exception as error:
		print(error)
		connection.rollback()

		error_message = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}

		return jsonify(error_message), 500		
	finally:
		cursor.close()
		connection.close()

@app.route("/api/user/auth", methods=["GET"])
def checkUsers():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		authorization_header = request.headers.get("Authorization")
		bearer_token = authorization_header.split(" ")[1]

		if bearer_token == "null":
			return jsonify({"data" : None}), 200

		payload = jwt.decode(bearer_token, secret_key, algorithms=["HS256"])
		id = payload["id"]

		query = "SELECT id, name, email, password FROM users WHERE id=%s"
		cursor.execute(query, (id,))
		select_data = cursor.fetchone()

		if select_data:
			userData = {
				"id": select_data["id"],
				"name": select_data["name"],
				"email": select_data["email"]
			}

			return jsonify({"data" : userData}), 200
		else:
			return jsonify({"data" : None}), 200
	except Exception as error:
		print(error)
		connection.rollback()
	finally:
		cursor.close()
		connection.close()

@app.route("/api/booking", methods=["POST"])
def add_booking():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		new_data = request.get_json()		
		authorization_header = request.headers.get("Authorization")
		bearer_token = authorization_header.split(" ")[1]

		if bearer_token == "null":
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403

		payload = jwt.decode(bearer_token, secret_key, algorithms=["HS256"])
		id = payload["id"]

		query = """
		SELECT u.id, b.users_id
		FROM users AS u
		LEFT JOIN bookings AS b ON u.id=b.users_id
		WHERE u.id=%s
		"""
		cursor.execute(query, (id,))
		select_data = cursor.fetchone()

		id = select_data["id"]
		attractionId = new_data["attractionId"]
		date = new_data["date"]
		time = new_data["time"]
		price = new_data["price"]

		if select_data and not select_data["users_id"]:
			query = "INSERT INTO bookings(users_id, attractions_id, date, time, price) VALUES(%s, %s, %s, %s, %s)"
			cursor.execute(query, (id, attractionId, date, time, price))
			connection.commit()

			return jsonify({"ok" : True}), 200
		elif select_data and select_data["users_id"]:
			query = "UPDATE bookings SET attractions_id=%s, date=%s, time=%s, price=%s WHERE users_id=%s"
			cursor.execute(query, (attractionId, date, time, price, id))
			connection.commit()

			return jsonify({"ok" : True}), 200
		else:
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403
	except Exception as error:
		print(error)
		connection.rollback()

		error_message = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}

		return jsonify(error_message), 500		
	finally:
		cursor.close()
		connection.close()

@app.route("/api/booking", methods=["GET"])
def get_booking():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		authorization_header = request.headers.get("Authorization")
		bearer_token = authorization_header.split(" ")[1]

		if bearer_token == "null":
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403

		payload = jwt.decode(bearer_token, secret_key, algorithms=["HS256"])
		id = payload["id"]

		query = """
		SELECT u.id AS users_id, b.users_id AS booking_id, DATE_FORMAT(b.date, "%Y-%m-%d") AS date, b.time, b.price, a.id, a.name, a.address, i.url
		FROM users AS u
		LEFT JOIN bookings AS b ON u.id=b.users_id		
		LEFT JOIN attractions AS a ON a.id=b.attractions_id
		LEFT JOIN images AS i ON a.id=i.attractions_id
		WHERE u.id=%s
		LIMIT 1
		"""
		cursor.execute(query, (id,))
		select_data = cursor.fetchone()

		if select_data and select_data["booking_id"]:
			final_data = {
				"data" : {
					"attraction" : {
						"id" : select_data["id"],
						"name" : select_data["name"],
						"address" : select_data["address"],
						"image" : select_data["url"]
					},
					"date" : select_data["date"],
					"time" : select_data["time"],
					"price" : select_data["price"]			
				}
			}

			return jsonify(final_data), 200
		elif select_data and not select_data["booking_id"]:
			final_data = {"data": None}

			return jsonify(final_data), 200
		else:
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403
	except Exception as error:
		print(error)
		connection.rollback()

		error_message = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}

		return jsonify(error_message), 500		
	finally:
		cursor.close()
		connection.close()

@app.route("/api/booking", methods=["DELETE"])
def delete_booking():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		authorization_header = request.headers.get("Authorization")
		bearer_token = authorization_header.split(" ")[1]

		if bearer_token == "null":
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403

		payload = jwt.decode(bearer_token, secret_key, algorithms=["HS256"])
		id = payload["id"]

		query = """
		SELECT u.id, b.users_id
		FROM users AS u
		LEFT JOIN bookings AS b ON u.id=b.users_id
		WHERE u.id=%s
		"""
		cursor.execute(query, (id,))
		select_data = cursor.fetchone()
		connection.commit()

		if select_data and select_data["users_id"]:
			delete_id = select_data["users_id"]

			delete_query = "DELETE FROM bookings WHERE users_id=%s"
			cursor.execute(delete_query, (delete_id,))
			connection.commit()

			return jsonify({"ok": True}), 200
		else:
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403
	except Exception as error:
		print(error)
		connection.rollback()

		error_message = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}

		return jsonify(error_message), 500
	finally:
		cursor.close()
		connection.close()

# 自訂訂單編號
def create_order_number():
	order_number = str(time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))+str(time.time()).replace(".", "")[-4:])
	return order_number

@app.route("/api/orders", methods=["POST"])
def add_orders():
	connection = connection_pool.get_connection()
	cursor = connection.cursor(dictionary=True)

	try:
		data = request.get_json()
		authorization_header = request.headers.get("Authorization")
		bearer_token = authorization_header.split(" ")[1]

		if bearer_token == "null":
			wrong_message = {
				"error": True,
				"message": "未登入系統，拒絕存取"
			}

			return jsonify(wrong_message), 403

		payload = jwt.decode(bearer_token, secret_key, algorithms=["HS256"])
		id = payload["id"]

		number = create_order_number()
		order = data["order"]["trip"]
		contact = data["order"]["contact"]
		attraction = data["order"]["trip"]["attraction"]

		query = "INSERT INTO orders(users_id, attractions_id, number, status, name, email, phone, date, time, price) VALUE (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
		cursor.execute(query, (id, attraction["id"], number, 1, contact["name"], contact["email"], contact["phone"], order["date"], order["time"], data["order"]["price"]))
		connection.commit()

		delete_query = "DELETE FROM bookings WHERE users_id=%s"
		cursor.execute(delete_query, (id,))
		connection.commit()

		# 傳資料給 Tappay 端
		test_url = "https://sandbox.tappaysdk.com/tpc/payment/pay-by-prime"
		partner_key = tappay_partner_key

		tappay_headers = {
			"Content-Type": "application/json",
			"x-api-key": partner_key
		}

		tappay_payload = {
			"prime": data["prime"],
			"partner_key": partner_key,
			"merchant_id": tappay_merchant_id,
			"order_number": number,
			"details": "TapPay Test",
			"amount": data["order"]["price"],
			"cardholder": {
				"phone_number": contact["phone"],
				"name": contact["name"],
				"email": contact["email"],
			},
			"remember": True
		}
		payload_json = json.dumps(tappay_payload)
		
		tappay_response = requests.post(test_url, data=payload_json, headers=tappay_headers)
		tappay_response_json = tappay_response.json()

		if tappay_response_json["status"] == 0:
			success_query = "UPDATE orders SET status=0 WHERE number=%s"
			cursor.execute(success_query, (number,))
			connection.commit()

			success_response = {
					"data": {
						"number": number,
						"payment": {
						"status": 0,
						"message": "付款成功"
						}
					}
				}

			return jsonify(success_response), 200
		else:
			fail_response = {
				"data": {
					"number": number,
					"payment": {
					"status": 1,
					"message": "付款失敗"
					}
				}
			}

			return jsonify(fail_response), 200
	except Exception as error:
		print(error)
		connection.rollback()

		error_message = {
			"error": True,
 			"message": "伺服器內部錯誤"
		}

		return jsonify(error_message), 500
	finally:
		cursor.close()
		connection.close()

app.run(host="0.0.0.0", port=3000, debug=True)