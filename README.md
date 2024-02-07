# CDA3101-ZybooksSubmit
Script for submitting grades from zybooks to canvas

- `student_mapping.csv` is a file that was semi-manually generated by going to the gradebook on canvas and exporting all the grades.
	- I've removed everything but the sid and email, as other content isn't necessary for this script
	- See [here](https://support.canvas.fsu.edu/kb/article/1524-how-can-i-easily-get-a-list-of-my-students-email-addresses-in-canvas/)



## How to use?

Create a file called `config.yml` based on `example_config.yaml`

```bash
pip3 install -r requirements.txt
python3 main.py
```

## TODO

Make sid_student_mapping optional. This file technically isn't required, but is used to make grading more accurate when students did not sign up with an `@ufl.edu` email
