protobuf2rosmsg.py is a basic python script that converts turns protobuf
messages and services into ROS .msg and .srv files respectively.


| argument      | descrption     |
| ------------- | ------------- |
| -f, --file             |   the relative file path to your .proto file                             |
| -m, --msg_dest         |   the path to the destination folder which generated .msg files should be create     |
| -s, --srv_dest         |   the path to the destination folder which generated .srv files should be create     |
| -c, --clean            |   removes pre-existing .msg and .srv files in the destination folders. (Warning this includes files not previously generated from this script) |
| -C, --clean_folders    |   removes pre-existing .msg and .srv files in the destination folders. (Warning this includes files not previously generated from this script) |

### Usage
protobuf2rosmsg.py [-f YOUR-FILE.proto] [-m PATH-TO-MSG_DEST] [-s
PATH-TO-SRV-DEST] [-c|-C]


Within the example folder there is a ros_schema.proto, a run.bat and clean.bat that
shows how this script can be used