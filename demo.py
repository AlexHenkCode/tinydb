from tinydb import TinyDB, Query

db = TinyDB('test.json')
table = db.table('users')

table.add_unique('password')

table.insert({
    'username': 'john',
    'password': '12345'
})

# Повторне значення має викликати помилку
table.insert({
    'username': 'alice',
    'password': '12345111'
})

# Читання всіх записів
print('All records:')
print(db.all())

# Пошук за паролем
User = Query()

print('Search by password:')
print(db.search(User.password == '12345'))

db.close()