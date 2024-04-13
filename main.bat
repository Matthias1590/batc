var str: *char = "hello\n"


func main() -> void {
    print_str(str)
    print_i8(123)
}

func print_str(str: *char) -> void {
    if (*str == '\0') {
        # ...
    } else if (*str == '\n') {
        # ...
    }
}
