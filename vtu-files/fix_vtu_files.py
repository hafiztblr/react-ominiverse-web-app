#!/usr/bin/env pvpython
import os
import glob
import struct
import numpy as np
import vtk
from vtk.util import numpy_support

cell_data_offsets = {
    'EP_G': 26188,
    'P_G': 28992,
    'Gas_Velocity': (31796, 3),
    'Solids_Velocity_1': (40200, 3),
    'Solids_Velocity_2': (48604, 3),
    'Gas_temperature': 57008,
    'Solids_temperature_1': 59812,
    'Solids_temperature_2': 62616,
    'O2_Gas_mass_fractions_1': 65420,
    'N2_Gas_mass_fractions_2': 68224,
    'H2O_Gas_mass_fractions_3': 71028,
    'CO_Gas_mass_fractions_4': 73832,
    'CO2_Gas_mass_fractions_5': 76636,
    'H2_Gas_mass_fractions_6': 79440,
    'CH4_Gas_mass_fractions_7': 82244,
    'TAR_Gas_mass_fractions_8': 85048,
    'TAR0_Gas_mass_fractions_9': 87852,
    'BIOMASS_Solids_mass_fractions_1_1': 90656,
    'MOISTURE_Solids_mass_fractions_1_2': 93460,
    'CHAR_Solids_mass_fractions_1_3': 96264,
    'ASH_Solids_mass_fractions_1_4': 99068,
}

def convert_file(infile):
    with open(infile, 'rb') as f:
        content = f.read()

    idx = content.find(b'<AppendedData')
    if idx == -1:
        # File is already in clean ASCII format
        return
    appended_start = content.find(b'_', idx)
    raw_bytes = content[appended_start+1 : content.rfind(b'</AppendedData>')]

    def read_array(offset, dtype, byte_order='>'):
        header = struct.unpack(byte_order + 'I', raw_bytes[offset:offset+4])[0]
        data_bytes = raw_bytes[offset+4 : offset+4+header]
        arr = np.frombuffer(data_bytes, dtype=dtype)
        if byte_order == '>':
            arr = arr.byteswap().astype(dtype, copy=False)
        return arr

    pts_data = read_array(0, np.float32).reshape(-1, 3)
    conn_data = read_array(9376, np.int32)
    off_data = read_array(20580, np.int32)
    types_data = read_array(23384, np.int32)

    grid = vtk.vtkUnstructuredGrid()
    
    # Points
    points = vtk.vtkPoints()
    points.SetData(numpy_support.numpy_to_vtk(pts_data, deep=True))
    grid.SetPoints(points)

    # Cells
    prev_off = 0
    for i in range(len(off_data)):
        curr_off = off_data[i]
        c_nodes = conn_data[prev_off:curr_off]
        prev_off = curr_off
        c_type = types_data[i]
        
        id_list = vtk.vtkIdList()
        for nid in c_nodes:
            id_list.InsertNextId(int(nid))
        grid.InsertNextCell(int(c_type), id_list)

    # Cell Data
    for name, item in cell_data_offsets.items():
        if isinstance(item, tuple):
            off, comps = item
            arr = read_array(off, np.float32).reshape(-1, comps)
        else:
            off = item
            arr = read_array(off, np.float32)
        
        vtk_arr = numpy_support.numpy_to_vtk(arr, deep=True)
        vtk_arr.SetName(name)
        grid.GetCellData().AddArray(vtk_arr)

    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(infile)  # overwrite existing VTU file with clean ASCII format
    writer.SetDataModeToAscii()
    writer.SetInputData(grid)
    writer.Write()

def main():
    import re
    all_files = sorted(glob.glob('ENTIRE_DOMAIN_*.vtu'))
    files = [f for f in all_files if re.match(r'^ENTIRE_DOMAIN_\d{4}\.vtu$', f)]
    print(f"Converting {len(files)} VTU files to clean ParaView format...")
    
    for idx, filepath in enumerate(files):
        convert_file(filepath)
        if (idx + 1) % 50 == 0 or (idx + 1) == len(files):
            print(f"Processed {idx + 1}/{len(files)} files...")

    print("All files converted successfully!")

if __name__ == '__main__':
    main()
