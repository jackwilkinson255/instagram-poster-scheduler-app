import React, { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import 'react-dropzone-uploader/dist/styles.css'
import Dropzone from 'react-dropzone-uploader'


const outerDiv = {
	backgroundColor: 'black',
	textAlign: 'center',
	fontWeight: 100,
	color: 'black',
	width: '100%',
	height: '300px',
	alignItems: "centre",
	border: "5px solid",
	top: "10%",
	transform: "translate (0, -50%)",
	padding: "10px",
};

const baseStyle = {
	align: "center",
	padding: '0px 0px 0px 0px',
	borderWidth: 2,
	borderColor: '#eeeeee',
	borderStyle: 'none',
	backgroundColor: 'black',
	color: '#bdbdbd',
	outline: 'none',
	transition: 'border .24s ease-in-out',
	width: "50%",
	height: "100%",
	justifyContent: "center",
  };

const inputLabelAccept = {
	background: '#242424',
	width: '100%',
	height: '100%',
}


const DragDropZone = (props) => {
	const [files, setFiles] = useState([]);
	const MAX_FILES = 10;

	const getUploadParams = ({ meta }) => {
		const url = 'https://httpbin.org/post'
		return { url, meta: { fileUrl: `${url}/${encodeURIComponent(meta.name)}` } }
	}

	const handleSubmit = (files, allFiles) => {
		let currentFiles = [...files]

		files.forEach(file => {
			const h = 4;
			const w = Math.round(h * (file.meta.width / file.meta.height));
			Object.assign(file, {
			name: file.name,
			path: file.meta.name,
			preview: file.meta.previewUrl,
			width: w,
			height: h
			})
		})

		setFiles(currentFiles);
		props.getImages(currentFiles);
	}

	function fileValidator(file) {
		let currentFiles = [...files, file];
		if (currentFiles.length >= MAX_FILES){
			return {
				code: "name-too-large",
				message: `Too many files`
			};
		}
		return null
	}


	const {getRootProps, getInputProps} = useDropzone({
		accept: {
		  'image/*': []
		},
		validator: fileValidator,
		onDrop: acceptedFiles => {
			let currentFiles = [...files]

			acceptedFiles.some((file) => {
				// let width = Math.round(height * (img_width / img_height));
				currentFiles.push(Object.assign(file, {
					name: file.name,
					preview: URL.createObjectURL(file),
					width: 3,
					height: 4
				}))
			});
			setFiles(currentFiles);
			props.getImages(currentFiles);
		}
	  });

	return (
			<div style={outerDiv}>
				<Dropzone
					getUploadParams={getUploadParams}
					onSubmit={handleSubmit}
					accept="image/*"
					inputContent="Drag Files"
					submitButtonContent="Upload Photos"
					styles={{
						dropzoneReject: { borderColor: 'red', backgroundColor: '#DAA' },
						submitButton: {name: 'red'},
						inputLabel: inputLabelAccept,
						dropzone: baseStyle,
						hzScroll: {width: "100px", overflow: "auto", whiteSpace: "nowrap"},
						dzuDropzone: { borderWidth: "100px", width: "500%" }
					}}
					/>
			</div>
	);
}

export default DragDropZone;

