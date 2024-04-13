<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## Objects

The `Objects` class in Mongotoy facilitates querying documents from a MongoDB database, offering a variety of methods 
for filtering, sorting, limiting, and executing queries asynchronously. It is initialized with the document class
associated with the query set, a session object for database operations, and an optional depth for dereferencing 
referenced documents. Key features include document creation, filtering, sorting, skipping, and limiting. Asynchronous
iteration over the result set is supported, with methods to fetch all documents, retrieve a single document, fetch 
a document by its identifier, and count the number of documents.

`Objects` instances are created by initializing them with a [session](/gurcuff91/mongotoy/docs/database/#session) 
object. For instance:

````python
# Open db session
async with engine.session() as session:
    
    # Create objects from a Person document
    persons = session.objects(Person)
````

### Creating documents

The `create` method in the `Objects` class facilitates the creation of new documents within the database. It accepts
keyword arguments representing the data for the document, saves the document to the database using the associated 
session, and returns the newly created document instance. This method streamlines the process of adding new data to 
the database by providing a simple and intuitive interface.

````python
# Open db session
async with engine.session() as session:
    
    # Create new person
    persons = await session.objects(Person).create(**person_data)
````

### Filtering documents

The `filter` method in the `Objects` class allows users to specify filter conditions for database queries, facilitating
precise data retrieval based on user-defined criteria. It accepts a variable number of filter expressions and keyword 
arguments. These conditions are then combined with existing filters using logical `AND` operations, ensuring that the 
resulting query set accurately reflects the specified filtering criteria. 
See [querying expressions](#querying-expressions)

````python
# Open db session
async with engine.session() as session:
    
    # Get persons older than 21 years
    persons = session.objects(Person).filter(Person.age > 21)
````

### Sorting documents

The `sort` method in the `Objects` class allows users to specify sorting conditions for database queries, enabling 
ordered data retrieval based on user-defined criteria. It accepts multiple sort expressions as parameters and adds them
to the query set, ensuring that the result set is sorted accordingly.
See [filtering expressions](#filtering-expressions)

````python
# Open db session
async with engine.session() as session:
    
    # Order persons by dob descending
    persons = session.objects(Person).sort(-Person.dob)
````

### Limiting documents

With the `skip` and `limit` functions in the `Objects` class, you can precisely control the pagination of query results.
By using `skip`, you can specify the number of documents to skip in the result set, allowing you to bypass a certain 
number of documents before retrieving results. Conversely, the `limit` function lets you define the maximum number of 
documents to return in the result set, ensuring that only a specified number of documents are included in the output. 
These functions provide you with flexibility in navigating through large datasets and retrieving only the necessary
information, contributing to efficient data retrieval and processing.

````python
# Open db session
async with engine.session() as session:
    
    # Skip 1st person and obtain next 5 persons
    persons = session.objects(Person).skip(1).limit(5)
````

### Dereferencing documents

The `dereference_deep` property in the Objects class sets the depth of dereferencing for related documents during query
execution. This allows fine-grained control over how deeply nested documents are retrieved from the database. A value 
of `-1` indicates full dereferencing, `0` means no dereferencing (**default behavior**), and _positive values_ specify 
the number of levels to dereference. This property enhances flexibility in handling intricate data structures.

````python
# Open db session
async with engine.session() as session:
    
    # No dereferencing `dereference_deep=0` by default
    persons = session.objects(Person)
    
    # Dereferencing 1 level
    persons = session.objects(Person, dereference_deep=1)

    # Dereferencing all levels
    persons = session.objects(Person, dereference_deep=-1)
````

### Iterating documents

The `Objects` class enables asynchronous iteration over the result set of a database query. It executes the query 
asynchronously, yielding parsed document instances one by one. This function is essential for handling large datasets
efficiently, as it allows you to iterate over query results without blocking the event loop. By leveraging the 
asynchronous iteration, you can seamlessly process query results in an asynchronous manner, facilitating smooth and
responsive application behavior.

````python
# Open db session
async with engine.session() as session:
    
    # Iterate over all persons
    async for person in session.objects(Person):
        print(person)
````

### Fetching documents

The `fetch`, `fetch_one`, and `fetch_by_id` functions in the `Objects` class facilitate the retrieval of documents from
the database result set.

- **fetch**: Asynchronously retrieves all documents in the result set. It returns a list of parsed document instances, 
enabling comprehensive access to query results for further processing or display.

- **fetch_one**: Asynchronously retrieves a specific document from the result set. It returns a single-parsed document
instance, suitable for scenarios where only one result is expected.

- **fetch_by_id**: Asynchronously retrieves a document by its identifier from the result set. It returns a parsed 
document instance corresponding to the provided identifier, allowing for targeted document retrieval based on unique
identifiers.

These functions contribute to efficient data retrieval and manipulation by leveraging asynchronous operations, 
ensuring responsiveness and scalability in handling database queries.

/// warning | Attention
The `fetch_one` and `fetch_by_id` functions will raise a `mongotoy.errors.NoResultsError` when no document matches the
query and a `mongotoy.errors.ManyResultsError` if multiple documents are returned unexpectedly.
///

### Counting documents

The `count` function in the `Objects` class retrieves the total count of documents that match the specified query 
criteria. This method executes an asynchronous operation to determine the number of documents in the result set. It 
provides valuable insight into the size of the dataset returned by the query, enabling efficient management and 
analysis of data.

````python
# Open db session
async with engine.session() as session:
    
    # Counting all persons
    persons_count = await session.objects(Person).count()
````

## Querying Expressions

In Mongotoy, you have a variety of options for crafting queries to suit your needs. You can opt for a Pythonic approach,
using basic operands for simpler operations. Alternatively, you can leverage the `mongotoy.expressions.Query` class to 
access a comprehensive range of supported operands. If you're familiar with Django's querying style, Mongotoy also 
offers a similar syntax through `mongotoy.expressions.Q` function. Additionally, if you prefer to work with raw MongoDB
queries, you have the flexibility to execute them directly. With these diverse options, you can choose the querying 
method that best fits your requirements and preferences.

You can construct queries by utilizing Document fields along with Python operands and values, providing an intuitive 
and Pythonic approach. This method allows you to express basic operations with ease, making it ideal for simple queries.

Supported operand are:

- `==`: Represents equality comparison of the field.
- `!=`: Represents inequality comparison of the field.
- `>`: Represents greater-than comparison of the field.
- `>=`: Represents greater-than-or-equal-to comparison of the field.
- `<`: Represents less-than comparison of the field.
- `<=`: Represents less-than-or-equal-to comparison of the field.

````python
# Persons older than 21 years
Person.age > 21

# Persons from USA
Person.address.country == 'USA'
````

Mongotoy also supports logical operands such as `AND`, `OR`, and `NOT` to combine queries. These operators enable you
to create more complex and sophisticated query expressions by joining multiple conditions together.

Supported logic operand are:

- `&`: Represents the logical `AND` operation between two query expressions.
- `|`: Represents the logical `OR` operation between two query expressions.
- `~`: Represents the logical `NOT` operation on the query expression.

````python
# Persons older than 21 years and younger than 60 years
Person.age > 21 & Person.age < 60

# Non-USA persons
~Person.address.country == 'USA'
````

When concatenating multiple queries with logical operands like `AND` or `OR`, you can use parentheses to enclose 
related expressions, providing clearer grouping.

````python
# Persons older than 21 years and younger than 60 years, or persons from USA
(Person.age > 21 & Person.age < 60) | Person.address.country == 'USA'
````

/// warning | Attention
It's important to use parentheses correctly for expression grouping, as improper usage can lead to incorrect query
expressions.
///

Mongotoy's `mongotoy.expressions.Query` class empowers you to construct MongoDB query expressions with flexibility. 
It offers an array of methods for creating comparisons, enabling the crafting of complex queries. These methods serve
as a convenient interface for generating specific query expressions, tailored precisely to your requirements.

### Using Query class

### Using Q function 

### Using raw queries

## Sorting Expressions