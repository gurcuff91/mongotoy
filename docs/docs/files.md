<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## Bucket

The Bucket is a fundamental component for managing file storage within Mongotoy. Representing the default GridFS bucket
named `fs`, it offers a robust interface for seamless file operations. With functionalities including file search, 
uploads, existence checks, and access to revisions, the Bucket streamlines file management tasks. By ensuring 
consistency, reliability, and efficiency in handling file storage, it enhances the overall file management experience
within Mongotoy.

### Getting a bucket

Use the `session.fs()` method to obtain a Bucket object, which represents a 
[GridFS](https://www.mongodb.com/docs/manual/core/gridfs/) bucket named `fs`. 

````python
# Open db session
async with engine.session() as session:
    # Get a Bucket
    fs = session.fs()
````

### Creating files

To create a file, you can invoke the `create()` method in the Bucket. With support for parameters like source, metadata,
and chunk size, this method provides flexibility and customization options, ensuring efficient file management.

````python
# Create an image file
image = await fs.create('profile.jpeg', src=open('profile.jpeg'))
````

### Search revisions

You can effortlessly retrieve all _revisions_ associated with a specific file stored in the file system bucket through 
the `revisions()` method in the Bucket. This method provides access to historical file versions, facilitating version 
control and supporting comprehensive file analysis.

````python
# Get all revisions of profile.jpeg file
revisions = await fs.revisions(filename='profile.jpeg')
````

### File existence

To verify the existence of files within the designated bucket, you can use the `exist()` method in the Bucket. This 
method offers a straightforward approach to checking file presence within the bucket, enhancing file management 
efficiency.

````python
# Check if profile.jpeg file exists
exist = await fs.exist(filename='profile.jpeg')
````

/// note
As the Bucket class inherits from [Objects](/gurcuff91/mongotoy/docs/objects), it inherits all functionalities for 
filtering, sorting, and counting files.
///

## File

Handling files in Mongotoy becomes effortless when you integrate the `mongotoy.types.File` into your document structure.
This simple step allows you to create a field representing a [GridFS](https://www.mongodb.com/docs/manual/core/gridfs/)
object seamlessly. With the `mongotoy.types.File`, managing files within your Mongotoy documents becomes a breeze, 
enabling smooth storage and retrieval processes. This integration enhances the usability and flexibility of Mongotoy 
for you, empowering you to handle file-related operations with ease and confidence.

````python
from mongotoy import Document
from mongotoy.types import File

class Person(Document):
    image: File
````

### Creating revision

In Mongotoy, files are capable of having multiple revisions or versions, ensuring flexibility and version control within
your document storage. Creating a new revision of a file is a seamless process, as you can invoke the `create_revision()`
method in a `File` object.

````python
# Open db session
async with engine.session() as session:
    # Get a FsBucket
    fs = session.fs()
    
    # Create a new revision of person image
    await person.image.create_revision(fs, src=open('profile2.jpeg'))
````

### Download contents

To download the contents of files in Mongotoy, you can use the `download_to()` method available within a `File` object.
This method streamlines the process, allowing you to retrieve the file's contents effortlessly.

````python
# Open db session
async with engine.session() as session:
    # Get a FsBucket
    fs = session.fs()
    
    # Download person image
    await person.image.download_to(fs, dest=open('profile3.jpeg'))
````

### Streaming contents

To stream file contents in Mongotoy, you can use the `stream()` method provided within a `File` object. This method
returns a `FieldStream` object, equipped with capabilities to seamlessly stream file contents. See [streaming](#streaming)

````python
# Open db session
async with engine.session() as session:
    # Get a FsBucket
    fs = session.fs()
    
    # Stream person image
    stream = await person.image.stream(fs)
````

### Getting a revision

You can effortlessly [download](#download-contents) or [stream](#streaming-contents) any revision of a file by 
indicating the `revision` parameter in the `download_to()` and `stream()` methods, respectively. This parameter, 
represented by an integer value, denotes the relationship with the upload date of the revision.

Here's how revision numbers are defined:

- **0**: Represents the original stored file.
- **1**: Denotes the first revision.
- **2**: Signifies the second revision.
- **-2**: Refers to the second most recent revision.
- **-1**: Indicates the most recent revision.

````python
from io import BytesIO

contents = BytesIO()

# Download the original revision
await person.image.download_to(fs, dest=contents)

# Download first revision
await person.image.download_to(fs, dest=contents, revision=1)

# Download the most recent revision
await person.image.download_to(fs, dest=contents, revision=-1)
````

### Delete file

To delete a file from the database, you can invoke the `delete()` method available within a `File` object. 
This straightforward method facilitates the deletion process, ensuring efficient management of your database fields.

````python
# Open db session
async with engine.session() as session:
    # Get a FsBucket
    fs = session.fs()
    
    # Delete person image
    await person.image.delete(fs)
````

/// note
When deleting documents, _file fields_ within them do not trigger file deletion automatically. To remove files 
associated with documents, manual deletion is required using the `delete()` method within the `File` object.
///

## Streaming

Streaming in Mongotoy enables efficient data retrieval from [GridFS](https://www.mongodb.com/docs/manual/core/gridfs/),
facilitating seamless access to large files stored in the database and improving performance by minimizing latency. By
allowing data to be read and processed in chunks, streaming reduces memory usage and enhances scalability. With built-in
support for streaming in `File` objects, you can integrate streaming functionality into tasks such as file uploads, 
downloads, and data processing. Overall, streaming in Mongotoy empowers users to effectively work with large datasets 
while optimizing performance and resource utilization.

The Streams in Mongotoy offers the following methods for efficient file data retrieval:

- **read(size = -1)**: Read data from the file, allowing you to specify the number of bytes to read or read until 
the end of the file if not specified.

- **readchunk()**: Read a chunk of data from the file, providing you with chunk-based data retrieval.

- **readline(size = -1)**: Read a line from the file, with the option to specify the maximum number of bytes to
read or read until the end of the line if not specified.

- **seek(pos, whence = os.SEEK_SET)**: Moves the file pointer to a specified position, with options to 
specify the reference point for the seek operation.

- **seekable()**: Checks if the file is seekable, returning True if the file is seekable and False otherwise.

- **tell()**: Returns the current position of the file pointer, providing users with information about the current 
reading position within the file.

- **close()**: Closes the stream, ensuring proper resource management and cleanup.

````python
# Get the stream
stream = await person.image.stream(fs)

# Read all contents
contents = await stream.read()

# Seek to position 0
stream.seek(0)

# Read by chunks
for _ in range(person.image.chunks):
    chunk = await stream.readchunk()

# Close stream
stream.close()
````






