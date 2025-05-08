//MultistepForm.tsx
import { IFormData } from "./FormController";
import { useForm } from "react-hook-form";



interface IMultistepForm {
    formData: IFormData;
    setFormData: React.Dispatch<React.SetStateAction<IFormData>>;
    currentStep: number;
    setStep: React.Dispatch<React.SetStateAction<number>>;
}
  
  const steps = [
    "Personal Information",
    "Contact Information",
    "Location Details",
  ];
  
  const MultistepForm: React.FC<IMultistepForm> = ({
    formData,
    setFormData,
    currentStep,
    setStep,
  }) => {
    const {
      handleSubmit,
      control,
      formState: { errors },
      getValues,
    } = useForm<IFormData>({
      defaultValues: formData,
    });
  
    const handleNextStep = (data: IFormData) => {
      setFormData((prevData) => ({ ...prevData, ...data }));
      setStep((step) => step + 1);
    };
  
    const handleBackStep = () => {
      setStep((step) => step - 1);
    };
  
    const onSubmit = (data: IFormData) => {
      setStep((step) => step + 1);
      setFormData((prevData) => ({ ...prevData, ...data }));
      console.log("Final Data Submitted:", getValues());
    };
  
    return (
      <div>
        <div>
          <Stepper activeStep={currentStep - 1}>
            {steps.map((label, index) => (
              <Step key={index}>
                <StepLabel>
                  <Typography>{label}</Typography>
                </StepLabel>
              </Step>
            ))}\
          </Stepper>
          <form
            onSubmit={handleSubmit(currentStep === 3 ? onSubmit : handleNextStep)}
          >
            {currentStep === 1 && (
              <>
                <ReusableTextField
                  name="firstName"
                  control={control}
                  label="First Name"
                  rules={{ required: "First name is required" }}
                />
                <ReusableTextField
                  name="lastName"
                  control={control}
                  label="Last Name"
                />
                <ReusableTextField
                  name="age"
                  control={control}
                  label="Age"
                  type="number"
                />
              </>
            )}
            {currentStep === 2 && (
              <>
                <ReusableTextField
                  name="email"
                  control={control}
                  label="Email"
                  rules={{ required: "Email is required" }}
                />
                <ReusableTextField
                  name="contactNo"
                  control={control}
                  label="Contact No"
                  type="number"
                />
              </>
            )}
            {currentStep === 3 && (
              <>
                <ReusableTextField name="city" control={control} label="City" />
                <ReusableTextField
                  name="country"
                  control={control}
                  label="Country"
                />
                <ReusableTextField
                  name="zipCode"
                  control={control}
                  label="Zip Code"
                  type="number"
                />
              </>
            )}
            <div>
              {currentStep > 1 && <Button>Back</Button>}
              <Button variant="contained" type="submit">
                {currentStep === 3 ? "Submit" : "Next"}
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  };
  
  export default MultistepForm;