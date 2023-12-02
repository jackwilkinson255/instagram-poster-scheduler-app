import React, {useEffect, useState} from "react";
import Title from "./components/Title";
import DragDropZone from "./components/DragDropZone";
import Gallery from "react-photo-gallery";
import Photo from "./components/Photo";
import {arrayMoveImmutable} from "array-move";
import { SortableContainer, SortableElement } from "react-sortable-hoc";
import 'bootstrap/dist/css/bootstrap.min.css';
import PostDetails from "./components/PostDetails";


const blankSpace = {
	position: 'top',
	bottom: '0px',
	height: '1200px',
	width: '100%',
	backgroundColor: 'black'
}

const galleryStyle = {
	// position: 'top',
	// bottom: '200px',
	// height: '300px',
	width: '100%',
	backgroundColor: 'black',
    targetRowHeight: '50px'
}

const SortablePhoto = SortableElement(item => <Photo {...item} />);
const SortableGallery = SortableContainer(({ items }) => (
  <Gallery photos={items} renderImage={props => <SortablePhoto {...props} />} />
));

function App() {
    const [items, setItems] = useState([]);
    const [files, setFiles] = useState([]);


    useEffect(() => {
        console.log("rendering now")
    }, []);



    const onSortEnd = ({ oldIndex, newIndex }) => {
        // Updates the order of the photo array
        setItems(arrayMoveImmutable(items, oldIndex, newIndex));
    };

    const getImages = (files) => {
        let photosUpdate = [];
        let filesUpdate = [];
        files.forEach((file) => {
            const newImage = {
                src: file.preview,
                width: file.width,
                height: file.height,
                name: file.file.name
            }
            photosUpdate.push(newImage)
            filesUpdate.push(file)

        })
        setItems(photosUpdate);
        setFiles(files);
    }



    return (
        <div >
            <div>
                <Title text="Instagram Poster" />
            </div>
            <div>
                <div className="gallery" style={galleryStyle}>
                    <SortableGallery items={items} onSortEnd={onSortEnd} axis={"xy"} />
                </div>

                <DragDropZone getImages={getImages}/>


            </div>


            <div>
                <PostDetails files={files} items={items} />
            </div>




            <div style={blankSpace}></div>
        </div>

    );
}

export default App;
