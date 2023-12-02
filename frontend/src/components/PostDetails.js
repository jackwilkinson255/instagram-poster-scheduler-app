import React, {useEffect, useState} from 'react'
import 'bootstrap/dist/css/bootstrap.min.css';
import '../css/App.css';
import '../css/Button.css'

export default function PostDetails({ files, items }) {
    const [caption, setCaption] = useState('')
    const [location, setLocation] = useState('')
    const [hashtags, setHashtags] = useState('')
    const [uploadStatus, setUploadStatus] = useState('Post')
    const [maxUploadId, setMaxUploadId] = useState(-1)
    const [buttonDisabled, setButtonDisabled] = useState(false)
    const [posting, setPosting] = useState(false)
    const [buttonClass, setButtonClass] = useState('Button');
    const completeText = "Post Successful!"

    const checkPostInfo = async () => {
        if (items.length === 0 || caption.length === 0 || location.length === 0 || hashtags.length === 0 || uploadStatus === completeText) {
            setButtonDisabled(true)
        } else {
            setButtonDisabled(false)
        }
        console.log()
    }

    useEffect(() => {
      const interval = setInterval(() => {
        checkPostInfo()
      }, 2000);
      return () => clearInterval(interval);
    }, [caption, location, hashtags, items]);

    const checkUploadStatus = async () => {
        const response = await fetch("http://127.0.0.1:8000/api/uploadstatus/")
        const status = await response.json()
        if (status.data > maxUploadId && posting === true){
            setUploadStatus(completeText)
        }
        setMaxUploadId(status.data)
        console.log("Max id is: " + status.data + "\tPosting: " + posting + "\tUpload status: " + uploadStatus)
      }

    useEffect(() => {
      const interval = setInterval(() => {
        checkUploadStatus()
      }, 2000);
      return () => clearInterval(interval);
    }, [posting, uploadStatus]);

    useEffect(() => {
        if (uploadStatus === completeText){
            setButtonClass("ButtonComplete")
        } else {
            setButtonClass("Button")
        }
    }, [uploadStatus]);

    const handleUploadPost = async () => {
        event.preventDefault()
        setPosting(true)
        setUploadStatus("Posting...")
        setButtonDisabled(true)

        const fileFormData = new FormData();

        files.forEach((file) => {
            fileFormData.append('files', file.file)
        })

        fileFormData.append(
            "caption",
            caption
        )

        fileFormData.append(
            "location",
            location
        )

        fileFormData.append(
            "hashtags",
            hashtags
        )

        items.forEach((item) => {
            fileFormData.append('image_order', item.name)
        })

        await fetch("http://127.0.0.1:8000/api/uploadimages/", {
            method: "POST",
            body: fileFormData
        }).then(response => {
            const status = response.json()
        })


    }

    return (
        <div className="card-body" style={{backgroundColor: 'black'}}>
            <div className="App list-group-item justify-content-center
            align-items-center mx-auto" style={{
                    "width": "400px",
                    "backgroundColor": "black"
                }}>
                <form>
                    <fieldset>
                        <input className="mb-2 form-control titleIn" onChange={
                            event => setCaption(event.target.value)} placeholder='Caption' />
                        <input className="mb-2 form-control desIn" onChange={
                            event => setLocation(event.target.value)} placeholder='Location' />
                        <input className="mb-2 form-control desIn" onChange={
                            event => setHashtags(event.target.value)} placeholder='Hashtags' minLength="10" />
                    </fieldset>
                    <center>
                        <button className={buttonClass}
                            onClick={handleUploadPost}
                            disabled={buttonDisabled}
                        >{uploadStatus}</button>
                    </center>
                </form>
            </div>
        </div>
    )
}
