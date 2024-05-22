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
referenced documents. Key features include filtering, sorting, skipping, and limiting. Asynchronous and synchronous
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

### Filtering documents

The `filter()` method in the `Objects` class allows users to specify filter conditions for database queries, facilitating
precise data retrieval based on user-defined criteria. It accepts a variable number of filter expressions and keyword 
arguments. These conditions are then combined with existing filters using logical `AND` operations, ensuring that the 
resulting query set accurately reflects the specified filtering criteria. 
See [querying expressions](#querying-expressions)

````python
# Open db session
async with engine.session() as session:
    
    # Get persons older than 21 years
    legal_persons = session.objects(Person).filter(Person.age > 21)
    
    # Get persons from USA
    usa_persons = session.objects(Person).filter(address__country__eq='USA')
````

/// note
The `filter()` method in the `Objects` class accepts all querying forms described in [querying expressions](#querying-expressions)  
///

### Sorting documents

The `sort()` method in the `Objects` class allows users to specify sorting conditions for database queries, enabling 
ordered data retrieval based on user-defined criteria. It accepts multiple sort expressions as parameters and adds them
to the query set, ensuring that the result set is sorted accordingly.
See [filtering expressions](#filtering-expressions)

````python
# Open db session
async with engine.session() as session:
    
    # Order persons by dob descending
    persons = session.objects(Person).sort(-Person.dob)
````

/// note
The `sort()` method in the `Objects` class accepts all sorting forms described in [sorting expressions](#sorting-expressions)  
///

### Limiting documents

With the `skip()` and `limit()` functions in the `Objects` class, you can precisely control the pagination of query results.
By using `skip()`, you can specify the number of documents to skip in the result set, allowing you to bypass a certain 
number of documents before retrieving results. Conversely, the `limit()` function lets you define the maximum number of 
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
of `-1` indicates full dereferencing, `0` means no dereferencing (**default behavior**), and positive values specify 
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

The `Objects` class enables asynchronous and synchronous iteration over the result set of a database query. It executes 
the query asynchronously or synchronously, yielding parsed document instances one by one. Those functions are essential 
for handling large datasets efficiently, as it allows you to iterate over query results without blocking the event loop.
By leveraging the asynchronous and synchronous iteration, you can seamlessly process query results in an asynchronous or 
synchronous manner.

````python
# Open db session
async with engine.session() as session:
    
    # Iterate over all persons
    async for person in session.objects(Person):
        print(person)
````

### Fetching documents

In Mongotoy, you have several options for fetching documents. The Objects class offers the following methods for 
retrieving data:

- **all()**: Retrieves all documents in the result set. It returns a list of parsed document instances, 
enabling comprehensive access to query results for further processing or display.

- **one()**: Retrieves a specific document from the result set. It returns a single-parsed document
instance. Raise `mongotoy.errors.NoResultError()` if no result found.

- **one_or_none()**: Retrieves a specific document from the result set. It returns a single-parsed document
instance or `None` if no result found.

- **get_by_id(value)**: Retrieves a document by its identifier from the result set. It returns a parsed 
document instance corresponding to the provided identifier.

These functions contribute to efficient data retrieval and manipulation by leveraging asynchronous or synchronous
operations, ensuring responsiveness and scalability in handling database queries.

````python
# Open db session
async with engine.session() as session:
    # Fetching all persons
    persons = await session.objects(Person).all()

    # Fetching one person
    person = await session.objects(Person).one()

    # Fetching one person by id
    person = await session.objects(Person).get_by_id(1)
````

### Counting documents

The `count()` function in the `Objects` class retrieves the total count of documents that match the specified query 
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
using basic operands for simpler operations. Alternatively, you can leverage the [Query class](#the-query-class) to 
access a comprehensive range of supported operands. If you're familiar with Django's querying style, Mongotoy also 
offers a similar syntax through [Q function](#the-q-function). Additionally, if you prefer to work with raw MongoDB
queries, you have the flexibility to execute them directly through [filter method](#filtering-documents). With these 
diverse options, you can choose the querying method that best fits your requirements and preferences.

You can construct queries by using Document fields along with Python operands and values, providing an intuitive 
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

### Logic operands

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

### The Query class

Mongotoy's `mongotoy.expressions.Query` class empowers you to construct MongoDB query expressions with flexibility. 
It offers an array of methods for creating comparisons, enabling the crafting of complex queries. These methods serve
as a convenient interface for generating specific query expressions, tailored precisely to your requirements.

Supported methods are:

- **Eq(field, value)**: Creates an equality query expression
- **Ne(field, value)**: Creates a not-equal query expression
- **Gt(field, value)**: Creates a greater-than query expression.
- **Gte(field, value)**: Creates a greater-than-or-equal query expression.
- **Lt(field, value)**: Creates a less-than query expression.
- **Lte(field, value)**: Creates a less-than-or-equal query expression.
- **In(field, value)**: Creates an 'in' query expression.
- **Nin(field, value)**: Creates a 'not in' query expression.
- **Regex(field, value)**: Creates a regex query expression.

````python
from mongotoy.expressions import Query

# Persons older than 21 years
Query.Gt(Person.age, 21)

# Persons from USA
Query.Eq(Person.address.country, 'USA')

# Non-USA persons
Query.Ne(Person.address.country, 'USA')

# Persons older than 21 years and younger than 60 years, or persons from USA
(Query.Gt(Person.age, 21) & Query.Lt(Person.age, 60)) | Query.Eq(Person.address.country, 'USA')
````

/// note
All methods in the `Query` class support _string values_ to specify fields.

````python
from mongotoy.expressions import Query

# Persons older than 21 years
Query.Gt('age', 21)
````

/// warning | Attention
To ensure accurate querying expressions, use the `alias` rather than the field `name` for fields with defined aliases. 
Otherwise, querying operations might target nonexistent database fields, resulting in inaccuracies.
///

### The Q function

The `mongotoy.expressions.Q` function is a flexible constructor for creating complex query expressions in a database. 
It accepts any number of keyword arguments, where each argument represents a field and its corresponding query 
condition. 

The function parses each keyword, separating the field name from the operator, which is connected by
**double underscores**. For instance, `name__eq` implies an **equality** check on the `name` field. The function then
dynamically constructs a query by combining these conditions using logical `AND` operations. This allows users to build
queries in a more readable and intuitive way, compared to manually constructing query strings.

The `Q` function is particularly useful in scenarios where the query parameters are not known in advance and need to be constructed at 
runtime based on user input or other dynamic data sources. It encapsulates the complexity of query construction, 
providing a clean and maintainable interface for building queries.

````python
from mongotoy.expressions import Q

# Persons older than 21 years
Q(age__eq=21)

# Persons from USA
Q(address__country__eq='USA')

# Non-USA persons
Q(address__country__ne='USA')

# Persons older than 21 years and younger than 60 years, or persons from USA
(Q(age__gt=21) & Q(age__lt=60)) | Q(address__country__eq='USA')
````

## Sorting Expressions

In Mongotoy, you have a variety of options for crafting sorting expressions to suit your needs. You can opt for a 
Pythonic approach, using basic operands for simpler operations. Alternatively, you can leverage the 
Sort class.

You can construct sorting expressions in Mongotoy by using document fields preceded with `-` for _descending_ or `+` for
_ascending_ directions, offering an intuitive and Pythonic approach. This method simplifies the expression of basic 
sorting criteria, making it ideal for straightforward sorting tasks.

````python
# Sort Persons descending by age
-Person.age

# Sort Persons ascending by age
+Person.age
````

### Multiple sorting

Mongotoy offers a seamless way to merge multiple sorting expressions using the `|` operator, providing you with a
powerful tool for constructing sophisticated sorting criteria effortlessly.

````python
# Sort Persons descending by age and ascending by date of birth (dob)
-Person.age | +Person.dob
````

### The Sort class

In Mongotoy, you can use the `mongotoy.expressions.Sort` class to effortlessly create versatile sorting expressions.
With clear representations and handy utility methods at your disposal, generating ascending and descending sort 
expressions becomes a breeze, streamlining your sorting operations.

Supported methods are:

- **Asc(*fields)**: Creates an ascending sort expressions
- **Desc(*fields)**: Creates a descending sort expressions

````python
from mongotoy.expressions import Sort

# Sort Persons descending by age
Sort.Desc(Person.age)

# Sort Persons ascending by age and date of birth
Sort.Asc(Person.age, Person.dob)

# Sort Persons descending by age and ascending by date of birth (dob)
Sort.Desc(Person.age) | Sort.Asc(Person.dob)
````

/// note
All methods in the `Sort` class support _string values_ to specify fields.

````python
from mongotoy.expressions import Sort

# Sort Persons descending by age and dob
Sort.Desc('age', 'dob')
````

/// warning | Attention
To ensure accurate sorting expressions, use the `alias` rather than the field `name` for fields with defined aliases. 
Otherwise, sorting operations might target nonexistent database fields, resulting in inaccuracies.
///
///