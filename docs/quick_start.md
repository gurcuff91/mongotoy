<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        display: none;
    }
</style>

## Installing

 To start using Mongotoy just run to install it:
 ```sh
 pip install mongotoy
 ```

Or, if using poetry:

```sh
poetry add mongotoy
```

## Quick Start
Let's get started with a minimal example by defining a document and performing CRUD(s) operations on the database.

```python
import asyncio
from mongotoy import Document, Engine
import datetime


class Person(Document):
    name: str
    last_name: str
    dob: datetime.date

    
# Create database engine
db = Engine('test-db')


async def main():
    # Create a new Person instance
    person = Person(
        name='John',
        last_name='Doe',
        dob=datetime.date(1990, 12, 25)
    )    
    
    # Connect to the MongoDB database.md
    await db.connect('mongodb://localhost:27017')
    
    # Open a database session
    async with db.session() as session:
        
        # Save the person to the database
        await session.save(person)
        
        # Fetch all persons from database
        async for c in session.objects(Person):
            print(c.dump_dict())
            
        # Update person dob
        person.dob=datetime.date(1995, 10, 25)
        await session.save(person)
        
        # Delete person from database
        await session.delete(person)


if __name__ == '__main__':
    asyncio.run(main())
```

This example demonstrates the usage of Mongotoy to interact with MongoDB databases in Python asynchronously.

Firstly, it defines a Person document class using Mongotoy's Document base class, specifying fields such 
as `name`, `last_name`, and `dob` (date of birth).

Then, it creates a database engine using `Engine('test-db')`, indicating the name of the MongoDB database to connect to.

Within the `main()` function:

1. A new Person instance named person is created with some sample data.
2. The script connects to the MongoDB database using `await db.connect('mongodb://localhost:27017')`.
3. A database session is opened using `async with db.session() as session`.
4. The person object is saved to the database using `await session.save(person)`.
5. All Person objects are fetched from the database using `async for c in session.objects(Person)`, and their details are printed.
6. The `dob` field of the person object is updated and the updated person object is saved back to the database.
7. Finally, the person object is deleted from the database using `await session.delete(person)`.
