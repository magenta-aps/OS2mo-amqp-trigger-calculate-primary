<!--
SPDX-FileCopyrightText: Magenta ApS

SPDX-License-Identifier: MPL-2.0
-->

# OS2mo AMQP Trigger Calculate Primary

OS2mo AMQP Trigger for recalculating primary.

## Usage
Adjust the `AMQP_HOST` variable to OS2mo's running message-broker, either;
* directly in `docker-compose.yml` or
* by creating a `docker-compose.override.yaml` file.

Add variables from MoraHelper and more.

Now start the container using `docker-compose`:
```
docker-compose up -d
```

You should see the following:
```
Establishing AMQP connection to amqp://guest:xxxxx@HOST:5672/
Creating AMQP channel
Attaching AMQP exchange to channel
Declaring unique message queue: os2mo-consumer-UUID
Binding routing-key: employee.engagement.edit
Listening for messages
```

At which point an update to an address in OS2mo should trigger an event similar to:
```
{
    "routing-key": "employee.address.update",
    "body": {
        "uuid": "be39de52-060a-4ae3-b705-ba46dd9b27a6",
        "time": "2021-07-27T00:00:00+02:00"
    }
}
```
