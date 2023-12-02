def get_lowest_id(self, files: list[str]) -> int:
    ids = []
    for file in files:
        if file.endswith(".jpg"):
            num_id = self.num_id_pattern.search(file)
            if num_id:
                ids.append(int(num_id.group()))

    if ids:
        return min(ids)
    else:
        return 0
