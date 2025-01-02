import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

def modify_file_settings(file_path, new_version):
    """修改文件中的MxCube.Version行和ProjectManager设置"""
    version_to_replace = None
    
    # 读取文件内容
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    # 修改内容并查找版本行和项目管理器设置
    for i, line in enumerate(lines):
        # 替换版本号
        if line.startswith("MxCube.Version="):
            version_to_replace = line.strip()  # 找到当前的版本行
            lines[i] = new_version + '\n'  # 替换当前行
        
        # 替换 ProjectManager.NoMain 和 ProjectManager.UnderRoot 设置
        if line.startswith("ProjectManager.NoMain="):
            lines[i] = "ProjectManager.NoMain=true\n"
        
        if line.startswith("ProjectManager.UnderRoot="):
            lines[i] = "ProjectManager.UnderRoot=false\n"
        
        # 替换 ProjectManager.functionlistsort 中的内容
        if line.startswith("ProjectManager.functionlistsort="):
            # 将HAL替换为LL，并将true替换为false
            line = line.replace("HAL", "LL").replace("true", "false")
            lines[i] = line
    
    # 写入修改后的内容
    with open(file_path, 'w') as file:
        file.writelines(lines)
    
    return version_to_replace  # 返回已替换的版本行

def create_simulink_model(matlab_folder, ioc_file):
    """通过MATLAB命令行创建Simulink模型"""
    model_name = 'model'
    matlab_command = f"""
    -sd "{matlab_folder}" -batch "modelName = '{model_name}';
    open_system(new_system(modelName));
    activeConfigObj = getActiveConfigSet(gcs);
    set_param(activeConfigObj, 'HardwareBoard', 'STM32F4xx Based');
    set_param(activeConfigObj, 'Solver', 'FixedStepDiscrete', 'FixedStep', '0.001');
    set_param(activeConfigObj,'StopTime','inf');
    cfg = get_param(activeConfigObj,'CoderTargetData');
    cfg.STM32CubeMX.ProjectFile = '{ioc_file}';
    set_param(activeConfigObj,'CoderTargetData',cfg);
    save_system(modelName);"
    """
    
    # 调用 MATLAB 命令行
    subprocess.run(['matlab'] + matlab_command.split(), check=True, shell=True)
    print(f"创建Simulink模型: {model_name}")

def main():
    new_version = "MxCube.Version=6.4.0"  # 定义新版本号
    script_directory = os.path.dirname(os.path.abspath(__file__))

    matlab_folder = os.path.join(script_directory, 'matlab')
    
    # 如果文件夹不存在，则创建它
    if not os.path.exists(matlab_folder):
        os.makedirs(matlab_folder)
        print(f"创建文件夹: {matlab_folder}")
    else:
        print(f"文件夹已存在: {matlab_folder}")
    
    # 查找当前目录下的.ioc文件并复制到matlab文件夹
    for filename in os.listdir(script_directory):
        if filename.endswith('.ioc'):
            source_file = os.path.join(script_directory, filename)
            destination_file = os.path.join(matlab_folder, filename)
            
            # 复制文件到新目录
            shutil.copy(source_file, destination_file)
            print(f"复制文件: {source_file} 到 {destination_file}")
            
            # 修改复制后的文件中的版本和项目管理器设置
            replaced_version = modify_file_settings(destination_file, new_version)
            if replaced_version:
                print(f"修改文件: {destination_file}, 从 {replaced_version.strip()} 修改为 {new_version}")
    
            # 创建Simulink模型文件
            create_simulink_model(matlab_folder, destination_file)

        if filename.endswith('.cproject'):
            source_file = os.path.join(script_directory, filename)
            tree = ET.parse(source_file)
            root = tree.getroot()

            for option in root.iter("option"):
                id_value = option.get("id")
                if "compiler.option.definedsymbols" in id_value:
                    value_list = ["USE_FULL_LL_DRIVER", "__MW_TARGET_USE_HARDWARE_RESOURCES_H__", "MW_TIMEBASESOURCE=TIM14"]
                    for value in value_list:
                        existing = any(child.tag == "listOptionValue" and child.get("value") == value for child in option)
                        if not existing:
                            print("Adding value: ", value)
                            new_element = ET.SubElement(option, "listOptionValue")
                            new_element.set("builtIn", "false")
                            new_element.set("value", value)

                if "compiler.option.includepaths" in id_value:
                    value_list = [r'"${workspace_loc:/${ProjName}/matlab/Core/Inc}"', r'"${workspace_loc:/${ProjName}/matlab/model_ert_rtw}"']
                    for value in value_list:
                        existing = any(child.tag == "listOptionValue" and child.get("value") == value for child in option)
                        if not existing:
                            print("Adding value: ", value)
                            new_element = ET.SubElement(option, "listOptionValue")
                            new_element.set("builtIn", "false")
                            new_element.set("value", value)

            for sourceEntries in root.iter("sourceEntries"):
                value_list = [r"matlab/Core/Src", r"matlab/STM32CubeIDE/Application/User/Core", r"matlab/model_ert_rtw"]
                for value in value_list:
                    #make dir for each value
                    os.makedirs(os.path.join(script_directory, value), exist_ok=True)
                    existing = any(child.tag == "entry" and child.get("name") == value for child in sourceEntries)
                    if not existing:
                        print("Adding value: ", value)
                        new_element = ET.SubElement(sourceEntries, "entry")
                        new_element.set("name", value)
                        new_element.set("kind", "sourcePath")
                        new_element.set("flags", "VALUE_WORKSPACE_PATH")

            # write to .cproject2 file
            with open(os.path.join(script_directory, filename + "2"), "wb") as f:
                # 添加 XML 声明和处理指令
                f.write(b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
                f.write(b'<?fileVersion 4.0.0?>\n')
                # 写入修改后的 XML 数据
                tree.write(f, encoding="utf-8", xml_declaration=False)







if __name__ == "__main__":
    main()
