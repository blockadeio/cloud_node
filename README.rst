Blockade.io Cloud Node
======================
Blockade is able to provide blocking capabilities within the Chrome browser by using a cloud backend controlled by trusted analysts. Blockade subscribes to the "serverless_" concept and uses nothing but Amazon Web Services (AWS_) for all its public functionality. This repository offers an alternative local instance that can be run on any server with an Internet connection. To learn more about Blockade, visit the project page_.

.. _serverless: https://aws.amazon.com/lambda/serverless-architectures-learn-more/
.. _AWS: https://aws.amazon.com
.. _page: https://www.blockade.io/

Install
-------

Install some depdencies first:

    $ sudo apt install python-pip python-dev libssl-dev libffi-dev mongodb-server

Get virtualenv:

    $ pip install virtualenv

Check out the repository and setup a virtualenv:

    $ virtualenv venv && source venv/bin/activate

Install the requirements

    $ pip install -r requirements.txt

Run the server using the local debug mode provided by Flask:

    $ python $REPOSITORY/app/api.py

Add your first administrator user:

    $ curl -X POST "http://localhost:5000/admin/add-user" \
           --data '{"user_email": "<EMAIL>", "user_name": "<NAME>", "user_role": "admin"}' \
           -H "Content-Type: application/json"

Perform any tests needed and deploy the server in a production_ capacity.

.. _production: http://flask.pocoo.org/docs/0.12/deploying/

Endpoints
---------
The following endpoints are exposed via this local node:

- **/<optional_db_route>/get-indicators**: Lists all the indicators for Blockade to consume
- **/<optional_db_route>/send-events**: Processes events collected from the browser using Blockade
- **/admin/add-user**: Add users to the local installation in order to contribute
- **/admin/validate-user**: Validate user against the local installation
- **/<optional_db_route>/admin/add-indicators**: Add indicators to the database from the toolbench_.
- **/<optional_db_route>/admin/get-events**: Get saved events from the database
- **/<optional_db_route>/admin/flush-events**: Flush events from the database

For more documentation, including CURL samples, start the server and browse it.

.. _toolbench: https://github.com/blockadeio/analyst_toolbench
.. _wiki: https://github.com/blockadeio/cloud_node/wiki/Endpoints

For users looking to host multiple databases on a single cloud node, replace the '<optional_db_route>' variable with the name of your database. This name will be used to load the database instance and perform actions on it.

Anything missing?
-----------------
.. image:: http://feathub.com/blockadeio/cloud_node?format=svg
     :target: http://feathub.com/blockadeio/cloud_node

Docker
---------
You can run cloud node in Docker.  To do so, build the container and run it, specifying the mongo host via environment variable::

    $ docker build -t cloud_node .
    $ docker run -d -p 5000:5000 --name cloud_node -e MONGO_HOST=<mongo hostname> cloud_node

Mac Note: if you want to run mongo on your localhost, you'll need to specify your machine's actual IP address for the <mongo host>.  Localhost WILL NOT WORK on a mac (but should on Linux).

Docker Note: if you wish to link to a container, called in this example mongo, your command would look like::

    $ docker run -d -p 5000:5000 --name cloud_node --link mongo:mongo -e MONGO_HOST=mongo cloud_node
