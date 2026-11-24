from tinydb import TinyDB, Query

db = TinyDB('demo.json')

# Додавання записів
db.insert({
    'username': 'john',
    'password': '12345'
})

db.insert({
    'username': 'alice',
    'password': '12345'
})

# Читання всіх записів
print('All records:')
print(db.all())

# Пошук за паролем
User = Query()

print('Search by password:')
print(db.search(User.password == '12345'))

db.close()