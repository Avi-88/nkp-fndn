//MultiStepFormController.tsx
import { useState } from "react";

export interface IFormData {
    firstName?: string;
    lastName?: string;
    age?: number | null;
    email?: string;
    contactNo?: number | null;
    city?: string;
    country?: string;
    zipCode?: number | null;
  }
  
  const initialFormData: IFormData = {
    firstName: "",
    lastName: "",
    age: 0,
    email: "",
    contactNo: 0,
    city: "",
    country: "",
    zipCode: 0,
  };
  
  const FormController = () => {
    const [formData, setFormData] = useState<IFormData>(initialFormData);
    const [step, setStep] = useState<number>(1);
  
    let currentContent: JSX.Element | undefined;
  
    switch (step) {
      case 1:
        currentContent = (
          <MultiStepForm
            currentStep={step}
            setStep={setStep}
            setFormData={setFormData}
            formData={{
              firstName: initialFormData.firstName,
              lastName: initialFormData.lastName,
              age: initialFormData.age,
            }}
          />
        );
        break;
      case 2:
        currentContent = (
          <MultiStepForm
            currentStep={step}
            setStep={setStep}
            setFormData={setFormData}
            formData={{
              email: initialFormData.email,
              contactNo: initialFormData.contactNo,
            }}
          />
        );
        break;
      case 3:
        currentContent = (
          <MultiStepForm
            currentStep={step}
            setStep={setStep}
            setFormData={setFormData}
            formData={{
              city: initialFormData.city,
              country: initialFormData.country,
              zipCode: initialFormData.zipCode,
            }}
          />
        );
        break;
      default:
        currentContent = (
          <Box>
            <Box>
              <Typography>
                Your details have been submitted successfully!
              </Typography>
  
              <Grid container spacing={2}>
                //Rendering Submitted Form Data
              </Grid>
            </Box>
          </Box>
        );
    }
  
    return <>{currentContent}</>;
  };
  
  export default FormController;