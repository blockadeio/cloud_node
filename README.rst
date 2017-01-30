Blockade.io Cloud Node
======================
Blockade is able to provide blocking capabilities within the Chrome browser by using a cloud backend controlled by trusted analysts. Blockade subscribes to the "serverless_" concept and uses nothing but Amazon Web Services (AWS_) for all its public functionality. This repository offers an alternative local instance that can be ran on any server with an Internet connection. To learn more about Blockade, visit the project page_.

.. _serverless: https://aws.amazon.com/lambda/serverless-architectures-learn-more/
.. _AWS: https://aws.amazon.com
.. _page: https://www.blockade.io/

Install
-------
Check out the repository and install the dependencies using PIP:

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

- **/get-indicators**: Lists all the indicators for Blockade to consume
- **/send-events**: Processes events collected from the browser using Blockade
- **/admin/add-user**: Add users to the local installation in order to contribute
- **/admin/add-indicators**: Add indicators to the database from the toolbench_.

.. _toolbench: https://github.com/blockadeio/analyst_toolbench
