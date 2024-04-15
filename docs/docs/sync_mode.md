<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## Sync mode

The sync mode in Mongotoy enables the integration of asynchronous functionalities into synchronous workflows. It 
offers features like enabling synchronous mode, wrapping asynchronous functions for synchronous execution, and 
converting asynchronous generators into synchronous ones. These tools allow you to seamlessly incorporate Mongotoy's 
asynchronous capabilities into synchronous applications, ensuring compatibility and flexibility across different 
programming paradigms.

To activate synchronous mode in your application, invoke the `mongotoy.enable_sync_mode()` function at the beginning of 
you code. Then, to use Mongotoy synchronously, you can remove all `await` keywords from Mongotoy function calls related 
to database operations. This straightforward approach allows for seamless integration of synchronous Mongotoy operations
into your application.

The `mongotoy.sync` module equips Mongotoy with essential utilities for seamlessly transitioning asynchronous 
functionality into synchronous operations, offering the following functions:

- **enable_sync_mode()**: Function to enable synchronous mode globally for running asynchronous functions synchronously.

- **run_sync(func)**: Wrapper function that runs an asynchronous function synchronously. It takes an 
asynchronous function as input and returns a wrapped function that can be called synchronously.

- **as_sync_gen(gen)**: Utility to convert an asynchronous generator into a synchronous generator. It 
yields items produced by the asynchronous generator in a synchronous manner.

- **proxy(func)**: Decorator to run an asynchronous function synchronously if sync mode is enabled. It wraps 
the asynchronous function, allowing it to be called synchronously when the sync mode is enabled.

Here is an example of how to write synchronous code:

````python
import io
import mongotoy

# Enable synchronous mode
mongotoy.enable_sync_mode()

# Open db session
with engine.session as session:
    # Upload person image
    person.image = session.fs().create('profile.jpeg', src=open('profile.jpeg'))

    # Save person
    session.save(person)

    # Download person image
    image = io.BytesIO
    person.image.download_to(session.fs(), dest=image)

    # Delete person image
    person.image.delete()

    # Delete person
    session.delete(person)
````

/// note
Bear in mind that although the code may appear _synchronous_, it actually functions asynchronously behind the scenes.
Mongotoy still relies on the asynchronous Motor driver for database interactions. The `mongotoy.sync` module simply 
provides an abstraction layer for executing operations in a synchronous fashion.
///