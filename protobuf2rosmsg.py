import re
from io import TextIOWrapper
import os
from typing import List, Union, Dict
# from typing import String
import argparse

parser = argparse.ArgumentParser(description="This proram generates ROS2 msg and srv files from a .proto source file")

parser.add_argument("-f", "--file", help="the relative file path to your .proto file", type=str)
parser.add_argument("-m", "--msg_dest", help="the path to the folder which generated .msg files should be create", type=str, dest="msg_dest", default="./")
parser.add_argument("-s", "--srv_dest", help="the path to the folder which generated .srv files should be create", type=str, dest="srv_dest", default="./")
parser.add_argument("-c","--clean", help="removes pre-existing .msg and .srv files in the destination folders. \n(Warning this includes files not previously generated from this script", action="store_true", dest="clean", default=False)
parser.add_argument("-C","--clean-folders", help="removes the .msg and .srv  destination folders. \n(Warning this includes files not previously generated from this script", action="store_true", dest="clean_folders", default=False)

class RepeatedField():
    def __init__(self, is_leaf: bool, val: str) -> None:
        self.is_leaf = is_leaf
        self.val = val
        

    def resolve(self, mf) -> str:
        if (self.is_leaf):
            return self.val + "[]"
        else:
            field = mf.get_repeat_field(self.val)
            if field == None:
                raise KeyError("Message definition not found within .proto file")
            return field.resolve(mf) + "[]"

class MessageField():
    def __init__(self, label, type, name, id, comment, meta_repeated):
        self.label = label
        self.type = type
        self.name = name
        self.id = id
        self.comment = comment
        self.meta_repeated = meta_repeated
        
    def resolve_type(self, mf) -> None:
        if self.meta_repeated:
            self.type = mf.get_repeat_field(self.type).resolve(mf)
            self.meta_repeated = False
    
    def to_string(self) -> str:
        msg_buffer = self.type.replace(".", "/")
        
        # Labels here
        if (self.label == "repeated"):
            msg_buffer += "[]"
            
        if (self.meta_repeated):
            msg_buffer += "[]"
        msg_buffer += " " + self.name + " " 
        
        if self.comment:
            msg_buffer += "#" + self.comment
        msg_buffer += "\n" 
        return msg_buffer
        
class Message():
    def __init__(self, title):
        self.title = title
        self.fields:List[MessageField] = []
        
    def add_field(self, label, type, name, id, comment, meta_repeated):
        self.fields.append(MessageField(label, type, name, id, comment, meta_repeated))
    
    def resolve_field_types(self, mf):
        for field in self.fields:
            field.resolve_type(mf)
    
    def create_msg_file(self, msg_dest: str):
        # print(type)
        # print(name)
        # print(comment)
        
        filepath = os.path.join(os.getcwd(), msg_dest, self.title + ".msg")
        print("message file path: ", filepath)
        f_msg: TextIOWrapper = open(filepath, "w")
        
        msg_str = self.to_string()
        
        # print(msg_str)
        f_msg.write(msg_str)
        f_msg.close()
    
    def to_string(self):
        msg_buffer = ""
        for field in self.fields:
            msg_buffer += field.to_string()
        return msg_buffer

class Service():
    def __init__(self, title, request_title: str, responce_title: str, srv_comment) -> None:
        self.title = title
        self.request_title: str = request_title
        self.responce_title: str = responce_title
        self.comment: str = srv_comment
    
    def create_srv_file(self, srv_dest: str, request: Message, responce: Message) -> None:
        filepath = os.path.join(os.getcwd(), srv_dest, self.title + ".srv")
        f_srv: TextIOWrapper = open(filepath, "w")
        
        request_str = request.to_string()
        responce_str = responce.to_string()
        
        srv_str = ""
        if self.comment:
            srv_str += "#" + self.comment + "\n"
        srv_str += request_str + "---\n" + responce_str
        
        # print(srv_str)
        f_srv.write(srv_str)
        f_srv.close()


class MessageFactory():
    def __init__(self):
        self.messages: List[Message] = []
        self.services: List[Service] = []
        self.repeat_fields: Dict[str, RepeatedField] = {}
        
    def set_repeat_field(self, key:str, val: RepeatedField) -> None:
        self.repeat_fields[key] = val
        
    def get_repeat_field(self, key: str) -> RepeatedField:
        field = self.repeat_fields.get(key)
        if field == None:
            raise KeyError(f"Type definition: {key} not yet found within .proto file. Can not repeat")
        return field
        
    def get_message(self, msg_title: str) -> Message:
        for msg in self.messages:
            if msg.title == msg_title:
                return msg
    
    def create_message(self, title) -> Message:
        msg_obj = Message(title)
        self.messages.append(msg_obj)
        return msg_obj
    
    def create_service(self, title, request_title: str, responce_title: str, srv_comment: str) -> None:
        # defers making the actual service Object until the end of parsing
        self.services.append(Service(title, request_title, responce_title, srv_comment))
    
    def pop_msg_by_title(self, msg_title) -> Union[Message, None]:
        for msg in self.messages:
            if msg.title == msg_title:
                self.messages.remove(msg)
                return msg
        return None
    
    def create_files(self, msg_dest: str, srv_dest: str) -> None:
        for service in self.services:
            request_msg = self.pop_msg_by_title(service.request_title)
            responce_msg = self.pop_msg_by_title(service.responce_title)
            
            if request_msg and responce_msg:
                service.create_srv_file(srv_dest, request_msg, responce_msg)
            else:
                raise SyntaxError
            
        # create msg files from left over messages
        for message in self.messages:
            message.resolve_field_types(self)
            message.create_msg_file(msg_dest)


def parse_protobuf(MF: MessageFactory, f_proto: TextIOWrapper, msg_dest: str, srv_dest: str):

    message = None
    service = None
    repeated_field = None
    message_obj = None
    for line in f_proto:
        importArg = re.search(r"import\s\"((?:\w+\/*)+)\/(\w+)\";", line)
        if (importArg):
            folder = importArg.group(1)
            file = importArg.group(2) + ".proto"
            
            
            proto_file_path = os.path.join(os.getcwd(), folder, file)
            print("import file path: ", proto_file_path)
            if os.path.isfile(proto_file_path):
                sub_f_proto: TextIOWrapper = open(proto_file_path, "r")
            
                parse_protobuf(MF, sub_f_proto, msg_dest, srv_dest)
            else:
                print("Can't import - File not found!")

        
        if not(message) and not(service) and not(repeated_field):
            # Find message headers
            message = re.match(r"^message\s(repeated)?([^\s\{]*)", line)
            # print(message)
            if (message):
                msg_title = message.group(2)
                if (message.group(1)):
                    message = None
                    repeated_field = msg_title
                else:
                    message_obj = MF.create_message(msg_title)
            
            
            # Find service headers
            service = re.match(r"^service\s*(\w+)\s*\{", line)
            # print(service)
            if (service):
                srv_header = service.group(1) #? Do we need this for anything?
        elif (repeated_field):
            groups = re.search(r"\s*(\w*)?\s(repeated)?(\S+)\s(\S+)\s?=\s?(\d*);\s*(?:(?:\/\*|\/)((?<=\/\*).*(?=\*\/))|(?:(?<=\/\/).*))?", line)
            if not(groups):
                # Find message terminator
                if (re.search(r"\}", line)):
                    repeated_field = None
                # skip empty/terminator/invalid lines
                continue
            
            rptd_f_repeated = groups.group(1) == "repeated" #protobuff's repeated keyword
            rptd_f_is_leaf = groups.group(2) == None #repeated affixed to type
            rptd_f_type = groups.group(3)
            
            MF.set_repeat_field(repeated_field, RepeatedField(rptd_f_is_leaf, rptd_f_type))


            
            
        elif (message):
            # search line for message contents
            groups = re.search(r"\s*(\w*)?\s(repeated)?(\S+)\s(\S+)\s?=\s?(\d*);\s*(?:(?:\/\*|\/)((?<=\/\*).*(?=\*\/))|(?:(?<=\/\/).*))?", line)
            if not(groups):
                # Find message terminator
                if (re.search(r"\}", line)):
                    message = None
                # skip empty/terminator/invalid lines
                continue
            
            # print(groups.groups())
            # append to file
            msg_f_label = groups.group(1)
            msg_f_meta_repeated = groups.group(2) == "repeated"
            msg_f_type = groups.group(3)
            msg_f_name = groups.group(4)
            msg_f_id = groups.group(5) # not needed for msg file
            msg_f_comment = groups.group(6)
            
            message_obj.add_field(msg_f_label, msg_f_type, msg_f_name, msg_f_id, msg_f_comment, msg_f_meta_repeated)
            
            
        elif (service):                
            groups = re.search(r"rpc\s*(\w+)\s*\((\w+)\)\s*returns\s*\((\w*)\);\s*(?:(?:\/\*|\/)((?<=\/\*).*(?=\*\/))|(?:(?<=\/\/).*))?", line)
            # print(groups)
            if not(groups):
                # Find message terminator
                if (re.search(r"\}", line)):
                    service = None
                # skip empty/terminator/invalid lines
                continue
            
            srv_title = groups.group(1)
            request_title = groups.group(2)
            responce_title = groups.group(3)
            srv_comment = groups.group(4)
                
            MF.create_service(srv_title, request_title, responce_title, srv_comment)

    f_proto.close()        
    # create files
    MF.create_files(msg_dest, srv_dest)

def main():
    
    # parse args
    args = parser.parse_args()    
    
    cwd = os.getcwd()
    print(cwd)
    
    # determind destination files
    msg_dest = args.msg_dest 
    if not os.path.isdir(msg_dest):
        os.makedirs(msg_dest)

    srv_dest = args.srv_dest 
    if not os.path.isdir(srv_dest):
        os.makedirs(srv_dest)
    
    
    # clean msg and srv folders
    if (args.clean or args.clean_folders):
        msg_dir_path = os.path.join(os.getcwd(), msg_dest)
        if os.path.isdir(msg_dir_path):
            for file_name in os.listdir(msg_dir_path):
                file_path = os.path.join(msg_dir_path, file_name)
                if os.path.isfile(file_path) and file_path.endswith('.msg'):
                    os.remove(file_path)
                
        srv_dir_path = os.path.join(os.getcwd(), srv_dest)
        if os.path.isdir(srv_dir_path):
            for file_name in os.listdir(srv_dir_path):
                file_path = os.path.join(srv_dir_path, file_name)
                if os.path.isfile(file_path) and file_path.endswith('.srv'):
                    os.remove(file_path)
            
        # remove folders
        if (args.clean_folders):
            if not os.path.samefile(os.getcwd(), msg_dir_path):
                os.rmdir(msg_dir_path)
            if not os.path.samefile(os.getcwd(), srv_dir_path):
                os.rmdir(srv_dir_path)
            print("cleaned msg and srv folders")
            return
        else:
            print("cleaned msg and srv files")
            
    
    # get proto file
    proto_file_path = args.file
    if proto_file_path:
        if os.path.isfile(proto_file_path):
            f_proto: TextIOWrapper = open(proto_file_path, "r")
            
            
            MF = MessageFactory()
            
            # create new messages and services from proto file
            header: str = f_proto.readline().replace("\n", "")
            if (re.search(r"(syntax\s?=\s?([\"'])proto3\2;)", header).group()):
                print("proto3 detected")
                parse_protobuf(MF, f_proto, msg_dest, srv_dest)
            else:
                print("defaulting to proto2")
                # TODO add default support for proto2
                print("Sorry, there is nothing implemented for proto2 ¯\_(ツ)_/¯")
                
        else:
            print("Input Error: .proto file not found at ", proto_file_path) 


if __name__ == "__main__":
    main()