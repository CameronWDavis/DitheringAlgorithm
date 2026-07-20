from array import array
from pathlib import Path
from datetime import datetime

MAX_WIDTH = 576
MAX_HEIGHT = 720
MACBINARY_LENGTH = 128
HEADER_LENGTH = 512

def bytes_to_bits(original: array) -> array:
    bits_array = array('B')

    for byte_index in range(0, len(original), 8):
        next_byte = 0
        for bit_index in range(8):
            next_bit = 1 - (original[byte_index + bit_index] & 1)
            next_byte = next_byte | (next_bit << (7 - bit_index))
            if (byte_index + bit_index + 1) >= len(original):
                break
        bits_array.append(next_byte)
    return bits_array

def prepare(data: array, width: int, height: int) -> array:
    bits_array = array('B')
    for row in range(height):
        image_location = row * width
        image_bits = bytes_to_bits(data[image_location:(image_location + width)])
        bits_array += image_bits
        remaining_width = MAX_WIDTH - width
        white_width_bits = array('B', [0] * (remaining_width // 8))
        bits_array += white_width_bits
    remaining_height = MAX_HEIGHT - height
    white_height_bits = array('B', [0] * ((remaining_height * MAX_WIDTH) // 8))
    bits_array += white_height_bits
    return bits_array

def run_length_encode(original_data: array) -> array:
    def take_same(source: array, start: int) -> int:
        count = 0
        while (start + count + 1 < len(source)
               and source[start + count] == source[start + count + 1]):
            count += 1
        return count + 1 if count > 0 else 0

    rle_data = array('B')
    for line_start in range(0, len(original_data), MAX_WIDTH // 8):
        data = original_data[line_start:(line_start + (MAX_WIDTH // 8))]
        index = 0
        while index < len(data):
            not_same = 0
            while (((same := take_same(data, index + not_same)) == 0)
                   and (index + not_same < len(data))):
                not_same += 1
            if not_same > 0:
                rle_data.append(not_same - 1)
                rle_data += data[index:index + not_same]
                index += not_same
            if same > 0:
                rle_data.append(257 - same)
                rle_data.append(data[index])
                index += same
    return rle_data

def macbinary_header(outfile: str, data_size: int) -> array:
    macbinary = array('B', [0] * MACBINARY_LENGTH)
    filename = Path(outfile).stem
    filename = filename[:63] if len(filename) > 63 else filename 
    macbinary[1] = len(filename) 
    macbinary[2:(2 + len(filename))] = array("B", filename.encode("mac_roman"))
    macbinary[65:69] = array("B", "PNTG".encode("mac_roman"))
    macbinary[69:73] = array("B", "MPNT".encode("mac_roman"))
    macbinary[83:87] = array("B", data_size.to_bytes(4, byteorder='big'))
    timestamp = int((datetime.now() - datetime(1904, 1, 1)).total_seconds())
    macbinary[91:95] = array("B", timestamp.to_bytes(4, byteorder='big'))
    macbinary[95:99] = array("B", timestamp.to_bytes(4, byteorder='big')) 
    return macbinary


def write_macpaint_file(data: array, out_file: str, width: int, height: int):
    bits_array = prepare(data, width, height)
    rle = run_length_encode(bits_array)
    data_size = len(rle) + HEADER_LENGTH 
    output = macbinary_header(out_file, data_size) + array('B', [0] * HEADER_LENGTH) + rle
    output[MACBINARY_LENGTH + 3] = 2 
    padding = 128 - (data_size % 128)
    if padding > 0:
        output += array('B', [0] * padding)
    with open(out_file + ".bin", "wb") as fp:
        output.tofile(fp)