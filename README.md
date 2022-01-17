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
Configuring calculate-primary logging
Acquiring updater: SD
Got class: <class 'integrations.calculate_primary.sd.SDPrimaryEngagementUpdater'>
Got object: <integrations.calculate_primary.sd.SDPrimaryEngagementUpdater object at 0x7fe055067a30>
Establishing AMQP connection to amqp://guest:xxxxx@msg_broker:5672/
Creating AMQP channel
Attaching AMQP exchange to channel
Declaring unique message queue: os2mo-consumer-db169240-4054-4818-a333-15ca41ba9835
Binding routing-key: employee.employee.create
Binding routing-key: employee.employee.edit
Binding routing-key: employee.employee.terminate
Binding routing-key: employee.engagement.create
Binding routing-key: employee.engagement.edit
Binding routing-key: employee.engagement.terminate
Listening for messages
```

At which point an update to an employee or engagement in OS2mo should trigger an event similar to:
```
{
    "routing-key": "employee.employee.edit",
    "body": {
        "uuid": "23d2dfc7-6ceb-47cf-97ed-db6beadcb09b",
        "object_uuid": "23d2dfc7-6ceb-47cf-97ed-db6beadcb09b",
        "time": "2022-01-04T00:00:00+01:00"
    }
}
Recalculating user: 23d2dfc7-6ceb-47cf-97ed-db6beadcb09b
```
