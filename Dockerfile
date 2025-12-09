FROM public.ecr.aws/lambda/python:3.11

# Install git
RUN yum update -y && yum install -y git && yum clean all

# Install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy source code
COPY src ${LAMBDA_TASK_ROOT}/src

# Set the CMD to your handler
CMD [ "src.main.handler" ]
